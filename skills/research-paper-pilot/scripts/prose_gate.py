#!/usr/bin/env python3
"""prose_gate.py: mechanical prose gate for paper drafts (LaTeX, Markdown, plain text).

What it does
  Strips LaTeX (comments, preamble, math, floats, citations, cross-references,
  formatting commands) or Markdown (code, tables, links), then scans the prose
  and reports rule hits with line numbers. It is advisory: it prints findings
  and exits 0. A human or an agent decides what to change.

Rules (ids are stable so reports can cite them)
  M1  em dashes per paragraph (cap per paragraph, none in the abstract)
  M2  pompous words (hard list always; soft list only as a cluster)
  M3  throat-clearing openers, repeated roadmaps, vague attribution with no citation
  M4  hype words, and "significant(ly)" in a sentence that carries no test
  M5  stacked hedges inside one sentence
  M6  runs of sentences with the same opening word; runs of connective-led paragraphs
  M7  uniform sentence length (low coefficient of variation) in a section
  M8  rule-of-three density (single-word triads)
  M9  staging tells: "not just X but Y", "serves as", inflated -ing riders
  M10 passive voice counts by section (reported, never a finding in protected sections)
  M11 reader load: label codes for conditions or instruments ("HA", "I5", "ORG-B"), and more
      coined names plus acronyms than the reader can hold (--term-budget); a coined name is a
      phrase set in italics at its first use and reused at least twice
  M12 number density: sentences and paragraphs that carry more numbers than a reader can follow
  M13 lists standing in for an argument: three or more short fragments in a body section, or a
      section whose text is mostly list items (contribution lists are exempt)

Academic mode (--academic) loosens thresholds and exempts what papers need:
  passive voice in Methods and appendices, one roadmap sentence, "not only ... but
  also", defined-term repetition, and citation sentences ("Smith et al. show").

Usage
  python prose_gate.py paper/main.tex --academic
  python prose_gate.py draft.md --json > gate.json
  python prose_gate.py paper/main.tex --academic --allow-terms ECE,OOD --term-budget 3

Exit codes: 0 normally; 2 if the input cannot be read; 1 only with --fail-on-findings.
Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import statistics
import sys
from collections import Counter, defaultdict

EM = "\u2014"
EN = "\u2013"
BREAK = "@@BREAK@@"
CITE_P = "[@c]"          # placeholder for a parenthetical citation (counts as no word)
AUTH = "AUTHORS"         # placeholder for a textual citation ("\citet")


# --------------------------------------------------------------------------
# LaTeX and Markdown cleaning (line numbers are preserved throughout)
# --------------------------------------------------------------------------

def balanced(s, i):
    """Index just after the brace group that opens at s[i] == '{', or -1."""
    depth = 0
    j = i
    n = len(s)
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return -1


def sub_balanced(s, pat, fn):
    """Replace every match of pat (which must end at an opening brace) plus its
    balanced brace group. fn(match, inner, whole) returns the replacement."""
    out = []
    pos = 0
    for m in pat.finditer(s):
        if m.start() < pos:
            continue
        end = balanced(s, m.end() - 1)
        if end < 0:
            continue
        out.append(s[pos:m.start()])
        out.append(fn(m, s[m.end():end - 1], s))
        pos = end
    out.append(s[pos:])
    return "".join(out)


def nl(text):
    return "\n" * text.count("\n")


def lineno(s, idx):
    return s.count("\n", 0, idx) + 1


FLOAT_RE = re.compile(
    r"\\begin\{((?:figure|table|wrapfigure|wraptable|sidewaystable|sidewaysfigure)\*?)\}(.*?)\\end\{\1\}", re.S)
MATH_ENV_RE = re.compile(
    r"\\begin\{((?:equation|align|alignat|gather|eqnarray|multline|flalign|displaymath|math)\*?)\}.*?\\end\{\1\}", re.S)
DROP_ENV_RE = re.compile(
    r"\\begin\{((?:tabular|tabularx|tabulary|longtable|array|verbatim|lstlisting|minted|thebibliography|"
    r"tikzpicture|algorithm|algorithmic|algorithm2e|comment)\*?)\}.*?\\end\{\1\}", re.S)
HEAD_RE = re.compile(r"\\(chapter|section|subsection|subsubsection|paragraph|subparagraph)(\*?)(?:\[[^\]]*\])?\{")
CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\{")
FOOTNOTE_RE = re.compile(r"\\(?:footnote|thanks)\{")
CITE_RE = re.compile(r"\\(cite[a-zA-Z]*|parencite|textcite|autocite|footcite|nocite)\*?(?:\[[^\]]*\])*\{[^}]*\}")
REF_RE = re.compile(r"\\(?:ref|eqref|autoref|cref|Cref|pageref|nameref|vref)\*?\{[^}]*\}")
MATH_RE = re.compile(r"\$\$.*?\$\$|\\\[.*?\\\]|\\\(.*?\\\)|\$[^$]*\$", re.S)
DROP_CMD_RE = re.compile(
    r"\\(?:label|input|include|includegraphics|bibliography|bibliographystyle|vspace|hspace|setlength|"
    r"thispagestyle|pagestyle|footnotemark|footnotetext|captionsetup|newcommand|renewcommand|"
    r"usepackage|graphicspath)\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*")
EMPTY_MACRO_RE = re.compile(r"\\[a-zA-Z]+\*?\{\}")
UNWRAP_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}")
LEFTOVER_CMD_RE = re.compile(r"\\[a-zA-Z]+\*?")


def math_token(m):
    """Placeholder for inline math: NUMMATH if it holds a digit, else MATH."""
    return ("NUMMATH" if re.search(r"\d", m.group(0)) else "MATH") + nl(m.group(0))


EMPH_TEX_RE = re.compile(r"\\(?:emph|textit|textsl)\{([A-Za-z][A-Za-z \-]{1,38})\}")
EMPH_MD_RE = re.compile(r"(?<![\w*])[*_]([A-Za-z][A-Za-z \-]{1,38})[*_](?![\w*])")


LIST_TEX_RE = re.compile(r"\\begin\{(itemize|enumerate|description)\}(.*?)\\end\{\1\}", re.S)


def latex_lists(s):
    """(start_line, end_line, item_word_counts, lead_text) for each list environment."""
    out = []
    prev_end = 0
    for m in LIST_TEX_RE.finditer(s):
        items = re.split(r"\\item\b(?:\[[^\]]*\])?", m.group(2))[1:]
        counts = [len(WORD_RE.findall(inline_clean(it))) for it in items]
        # the lead-in is the text since the previous list or heading, at most 300 characters
        lead = inline_clean(s[max(prev_end, m.start() - 300):m.start()].split(BREAK)[-1])
        prev_end = m.end()
        out.append((lineno(s, m.start()), lineno(s, m.end()), counts, lead))
    return out


def emphasised(s, pat):
    """(line, phrase) for each short italic phrase; candidates for coined names."""
    out = []
    for m in pat.finditer(s):
        phrase = collapse(m.group(1)).lower()
        if 1 <= len(phrase.split()) <= 3:
            out.append((lineno(s, m.start()), phrase))
    return out


def strip_comments(s):
    return re.sub(r"(?<!\\)%.*", "", s)


def inline_clean(s):
    """Clean one chunk of LaTeX body text. Newline count is preserved."""
    s = MATH_RE.sub(math_token, s)

    def cite(m):
        name = m.group(1)
        if name == "nocite":
            return nl(m.group(0))
        if name.startswith(("citet", "textcite", "citeauthor", "citealt")):
            return AUTH + nl(m.group(0))
        return CITE_P + nl(m.group(0))
    s = CITE_RE.sub(cite, s)
    s = REF_RE.sub(lambda m: "REF" + nl(m.group(0)), s)
    s = re.sub(r"\\url\{[^}]*\}", "URL", s)
    s = re.sub(r"\\href\{[^}]*\}\{([^{}]*)\}", r"\1", s)
    s = sub_balanced(s, FOOTNOTE_RE, lambda m, inner, whole: nl(inner))
    s = DROP_CMD_RE.sub(lambda m: nl(m.group(0)), s)
    s = EMPTY_MACRO_RE.sub("NAME", s)
    for _ in range(8):
        new = UNWRAP_RE.sub(r"\1", s)
        if new == s:
            break
        s = new
    s = LEFTOVER_CMD_RE.sub("", s)
    s = re.sub(r"\\\\(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\[,;:! @\-]", " ", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("~", " ")
    s = s.replace("``", '"').replace("''", '"')
    s = s.replace("---", EM).replace(" -- ", " " + EM + " ")
    s = re.sub(r"(?<=\w)--(?=\w)", EN, s)
    s = s.replace("\x01", "$")
    s = re.sub(r"[ \t]+", " ", s)
    return s


def clean_latex(raw):
    """Return (text, headings, captions, appendix_line).
    headings: list of (line, level, title). captions: list of (line, text)."""
    s = raw.replace("\r\n", "\n")
    s = strip_comments(s)
    m = re.search(r"\\begin\{document\}", s)
    if m:
        s = nl(s[:m.end()]) + s[m.end():]
    m = re.search(r"\\end\{document\}", s)
    if m:
        s = s[:m.start()] + nl(s[m.start():])
    s = s.replace("\\$", "\x01").replace("\\%", "%").replace("\\&", "&").replace("\\_", "_").replace("\\#", "#")

    captions = []

    def float_cb(m):
        body = m.group(2)
        base = m.start(2)
        for cm in CAPTION_RE.finditer(body):
            end = balanced(body, cm.end() - 1)
            if end > 0:
                captions.append((lineno(m.string, base + cm.start()), body[cm.end():end - 1]))
        return BREAK + nl(m.group(0))
    s = FLOAT_RE.sub(float_cb, s)
    s = MATH_ENV_RE.sub(lambda m: "MATH" + nl(m.group(0)), s)
    s = DROP_ENV_RE.sub(lambda m: BREAK + nl(m.group(0)), s)

    headings = []

    def head_cb(m, inner, whole):
        kind = m.group(1)
        level = {"chapter": 1, "section": 1, "subsection": 2, "subsubsection": 3}.get(kind, 4)
        title = re.sub(r"\\[a-zA-Z]+\*?|[{}$]", "", inner).strip()
        if level < 4:
            headings.append((lineno(whole, m.start()), level, title))
        return BREAK + nl(inner)
    s = sub_balanced(s, HEAD_RE, head_cb)

    def abs_cb(m):
        if m.group(1) == "begin":
            headings.append((lineno(m.string, m.start()), 1, "Abstract"))
        return BREAK + nl(m.group(0))
    s = re.sub(r"\\(begin|end)\{abstract\}", abs_cb, s)
    appendix_line = None
    am = re.search(r"\\appendix\b", s)
    if am:
        appendix_line = lineno(s, am.start())
        s = s[:am.start()] + BREAK + s[am.end():]
    emph = emphasised(s, EMPH_TEX_RE)
    lists = latex_lists(s)
    s = re.sub(r"\\item\b(?:\[[^\]]*\])?", BREAK, s)
    s = re.sub(r"\\begin\{minipage\}(?:\[[^\]]*\])?\{[^}]*\}", BREAK, s)
    s = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\[[^\]]*\])?", BREAK, s)
    text = inline_clean(s)
    caps = [(ln, inline_clean(t)) for ln, t in captions]
    headings.sort()
    return text, headings, caps, appendix_line, {"emph": emph, "lists": lists}


def clean_markdown(raw):
    lines = raw.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        for k in range(1, min(len(lines), 60)):
            if lines[k].strip() in ("---", "..."):
                for j in range(0, k + 1):
                    lines[j] = ""
                break
    out = []
    headings = []
    lists = []
    cur_list = None
    prev_text = ""
    in_code = False
    for ln, line in enumerate(lines, 1):
        bullet = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)", line) if not in_code else None
        if bullet and not re.match(r"^\s*([-*_]\s*){3,}$", line):
            if cur_list is None:
                cur_list = [ln, ln, [], prev_text]
                lists.append(cur_list)
            cur_list[1] = ln
            cur_list[2].append(len(WORD_RE.findall(bullet.group(1))))
        elif line.strip() and not line.startswith(("  ", "\t")):
            cur_list = None
        if line.strip() and not bullet:
            prev_text = line
        if re.match(r"^\s*(```|~~~)", line):
            in_code = not in_code
            out.append(BREAK)
            continue
        if in_code:
            out.append("")
            continue
        hm = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if hm:
            headings.append((ln, len(hm.group(1)), hm.group(2)))
            out.append(BREAK)
            continue
        if line.lstrip().startswith("|") or re.match(r"^\s*([-*_]\s*){3,}$", line):
            out.append(BREAK)
            continue
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", BREAK, line)
        out.append(line)
    s = "\n".join(out)
    s = re.sub(r"<!--.*?-->", lambda m: nl(m.group(0)), s, flags=re.S)
    s = re.sub(r"<[^>\n]+>", "", s)
    s = re.sub(r"`[^`\n]*`", "CODE", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]+)\]\((?:[^)]*)\)", r"\1", s)
    s = re.sub(r"\[(?:@[^\]]+)\]", CITE_P, s)
    s = re.sub(r"\[\d+(?:\s*[,\u2013-]\s*\d+)*\]", CITE_P, s)
    s = re.sub(r"\((?:[A-Z][A-Za-z\-]+(?:\s+et al\.|\s+and\s+[A-Z][A-Za-z\-]+)?,?\s+\d{4}[a-z]?(?:;[^)]*)?)\)",
               CITE_P, s)
    s = CITE_RE.sub(lambda m: CITE_P + nl(m.group(0)), s)
    s = MATH_RE.sub(math_token, s)
    s = re.sub(r"(\*\*|__)(.+?)\1", r"\2", s)
    emph = emphasised(s, EMPH_MD_RE)
    s = re.sub(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])", r"\1", s)
    s = s.replace("---", EM).replace(" -- ", " " + EM + " ")
    s = re.sub(r"(?<=\w)--(?=\w)", EN, s)
    s = re.sub(r"[ \t]+", " ", s)
    heads = []
    levels = sorted({h[1] for h in headings})
    top = levels[0] if levels else 1
    if levels and sum(1 for h in headings if h[1] == top) == 1 and len(levels) > 1:
        top = levels[1]
    for ln, lv, title in headings:
        if lv <= top:
            heads.append((ln, 1, title))
    return s, heads, [], None, {"emph": emph, "lists": [tuple(x) for x in lists]}


# --------------------------------------------------------------------------
# paragraphs, sentences
# --------------------------------------------------------------------------

class Para:
    def __init__(self, kind):
        self.kind = kind
        self.lines = []       # (line_no, text)
        self.text = ""
        self.offsets = []
        self.section = ""
        self.protected = False

    def finish(self):
        parts = []
        pos = 0
        self.offsets = []
        for ln, t in self.lines:
            self.offsets.append((pos, ln))
            parts.append(t)
            pos += len(t) + 1
        self.text = "\n".join(parts)
        self.starts = [o for o, _ in self.offsets]

    @property
    def start_line(self):
        return self.lines[0][0] if self.lines else 0

    @property
    def end_line(self):
        return self.lines[-1][0] if self.lines else 0

    def line_at(self, off):
        i = bisect.bisect_right(self.starts, off) - 1
        return self.offsets[max(i, 0)][1]


def build_paragraphs(text):
    paras = []
    cur = Para("body")

    def flush():
        nonlocal cur
        if cur.lines:
            cur.finish()
            paras.append(cur)
        cur = Para("body")
    for ln, line in enumerate(text.split("\n"), 1):
        if not line.strip():
            flush()
            continue
        pieces = line.split(BREAK)
        for k, piece in enumerate(pieces):
            if k > 0:
                flush()
            if piece.strip():
                cur.lines.append((ln, piece.strip()))
    flush()
    return paras


ABBR = ["e.g.", "i.e.", "et al.", "vs.", "cf.", "Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "Secs.", "Ref.",
        "No.", "approx.", "resp.", "etc.", "Dr.", "Mr.", "Ms.", "Prof.", "St.", "Tab.", "Alg."]
SPLIT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+(?=[\"'(\[]?[A-Z0-9\[])")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019\-./%][A-Za-z0-9]+)*%?")


def split_sentences(text):
    t = text
    for a in ABBR:
        t = t.replace(a, a.replace(".", "\x02"))
    sents = []
    last = 0
    for m in SPLIT_RE.finditer(t):
        sents.append((last, t[last:m.start()].replace("\x02", ".")))
        last = m.end()
    sents.append((last, t[last:].replace("\x02", ".")))
    return [(o, s) for o, s in sents if s.strip()]


def words_of(s):
    s = s.replace(CITE_P, " ")
    return WORD_RE.findall(s)


def collapse(s):
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# word lists
# --------------------------------------------------------------------------

HARD_WORDS = (
    r"delv(?:e|es|ed|ing)|tapestr(?:y|ies)|testament|realms?|multifaceted|intricacies|intricate|pivotal|"
    r"groundbreaking|game-?changing|transformative|unparalleled|seamless(?:ly)?|meticulous(?:ly)?|"
    r"commendable|vibrant|myriad|plethora|embark(?:s|ed|ing)?|unveil(?:s|ed|ing)?|unravel(?:s|ed|ing)?|"
    r"ever-(?:evolving|changing)|beacon|cornerstone|bedrock|symphony|paves? the way|paving the way|"
    r"navigat(?:e|es|ed|ing) the (?:complexit|landscape|nuance)\w*|rich tapestry|treasure trove"
)
SOFT_WORDS = (
    r"comprehensive|robust|novel|crucial|leverag(?:e|es|ed|ing)|harness(?:es|ed|ing)?|facilitat(?:e|es|ed|ing)|"
    r"utili[sz](?:e|es|ed|ing)|underscor(?:e|es|ed|ing)|highlight(?:s|ed|ing)?|shed(?:s|ding)? light|"
    r"landscape|paradigm|holistic|streamlin(?:e|es|ed|ing)|elevat(?:e|es|ed|ing)|empower(?:s|ed|ing)?|"
    r"unlock(?:s|ed|ing)?|foster(?:s|ed|ing)?|bolster(?:s|ed|ing)?|nuanced?|vital|essential|"
    r"a wide range of|a variety of|cutting-edge|in the realm|deep dive|profound(?:ly)?"
)
HYPE_WORDS = (
    r"remarkabl[ey]|unprecedented|dramatic(?:ally)?|strikingly|extremely|incredibl[ey]|tremendous(?:ly)?|"
    r"revolutionary|breakthrough|compelling|exceptional(?:ly)?|outstanding|impressive(?:ly)?|"
    r"astonishing(?:ly)?|spectacular(?:ly)?|dazzling|phenomenal(?:ly)?|undeniabl[ey]|unquestionabl[ey]|"
    r"powerful|undoubtedly"
)
THROAT = [
    r"it is (?:worth|important|crucial|essential|interesting|notable|noteworthy) (?:to note|noting|to mention|"
    r"to highlight|to emphasi[sz]e|to stress|to point out)",
    r"it should be (?:noted|emphasi[sz]ed|stressed|mentioned|pointed out)",
    r"(?:importantly|notably|interestingly|crucially|remarkably|needless to say),",
    r"in today'?s ", r"in (?:the )?(?:ever[- ]?(?:evolving|changing)|rapidly (?:evolving|changing))",
    r"in the realm of", r"as we all know", r"when it comes to", r"at the end of the day",
    r"let'?s (?:dive|delve|explore|take a)", r"here'?s (?:the|what)",
]
THROAT_RE = re.compile(r"^(?:" + "|".join(THROAT) + ")")
ROADMAP_RE = re.compile(
    r"\b(?:the (?:remainder|rest) of (?:this|the) (?:paper|article|work)|this (?:paper|article) is organi[sz]ed|"
    r"in the following sections)\b", re.I)
VAGUE_RE = re.compile(
    r"\b(?:(?:studies|research|prior work|previous work|existing work|recent work|the literature|researchers|"
    r"experts|scholars)\s+(?:has|have|had)?\s*(?:shown|show|shows|suggest|suggests|suggested|demonstrate|"
    r"demonstrates|demonstrated|found|find|finds|indicate|indicates|argue|argued|reported)|"
    r"it is (?:well[- ])?(?:known|established|documented|widely (?:believed|accepted)))\b", re.I)
HEDGE_WORDS = (
    r"may|might|could|possibly|perhaps|potentially|probably|arguably|presumably|seemingly|somewhat|"
    r"relatively|fairly|appears?|appeared|seems?|seemed|tends?|tended|suggest(?:s|ed)?|likely|plausibly"
)
HEDGE_RE = re.compile(r"\b(?:" + HEDGE_WORDS + r")\b", re.I)
HARD_RE = re.compile(r"\b(?:" + HARD_WORDS + r")\b", re.I)
SOFT_RE = re.compile(r"\b(?:" + SOFT_WORDS + r")\b", re.I)
HYPE_RE = re.compile(r"\b(?:" + HYPE_WORDS + r")\b", re.I)
SIGNIF_RE = re.compile(r"\bsignifican(?:t|tly)\b", re.I)
TEST_RE = re.compile(
    r"\b(?:p\s*[<=>]|p-value|t-test|test|tests|ci|confidence interval|bootstrap|wilcoxon|permutation|anova|"
    r"mann-whitney|chi-square|fdr|bonferroni|tost|mixed model|regression|effect size|MATH|NUMMATH)\b"
    r"|\b(?:NUM)?MATH\b", re.I)
CONNECTIVE_RE = re.compile(
    r"^(?:however|moreover|furthermore|additionally|in addition|overall|consequently|therefore|thus|"
    r"nevertheless|nonetheless|importantly|notably|in summary|in conclusion|taken together|ultimately)\b", re.I)
NOT_JUST_RE = re.compile(r"\bnot (?:just|merely|simply)\b[^.?!]{3,90}?\bbut\b", re.I)
NOT_ONLY_RE = re.compile(r"\bnot only\b[^.?!]{3,90}?\bbut\b", re.I)
COPULA_RE = re.compile(r"\b(?:serves?|serving|stands?|acts?|functions?) as (?:a|an|the)\b|"
                       r"\b(?:plays?|played) an? (?:crucial|key|pivotal|vital|significant|important) role\b", re.I)
RIDER1_RE = re.compile(r",\s+(?:highlighting|underscoring|showcasing|emphasi[sz]ing|reflecting|paving|"
                       r"cementing|solidifying|fostering|signal(?:l)?ing)\b", re.I)
RIDER2_RE = re.compile(r",\s+(?:demonstrating|illustrating|revealing|ensuring|enabling|contributing)\b", re.I)
TRIAD_RE = re.compile(r"\b([a-z][a-z-]+), ([a-z][a-z-]+),? (?:and|or) ([a-z][a-z-]+)\b")
PASSIVE_AUX = r"(?:is|are|was|were|be|been|being|get|gets|got)"
IRREG = (r"shown|found|made|given|taken|chosen|written|known|seen|drawn|run|set|built|held|kept|done|sent|"
         r"left|lost|put|read|split|cut|hidden|broken|driven|grown|thrown|understood|begun|withdrawn")
PASSIVE_RE = re.compile(
    r"\b" + PASSIVE_AUX + r"\s+(?:(?:not|also|then|first|further|already|never|always|\w+ly)\s+)*"
    r"((?:[a-z]{3,}ed)|(?:" + IRREG + r"))\b", re.I)
NOT_PARTICIPLE = {"need", "indeed", "speed", "seed", "feed", "bleed", "hundred", "embed", "red", "bed",
                  "proceed", "exceed", "succeed", "shed", "sacred", "naked", "wicked", "supposed", "interested",
                  "worried", "excited", "pleased", "scared"}
# M11: codes and coined names. A label code is a capitalised token the text never expands
# ("HA", "I5", "ORG-B", "H-probe"); an acronym is one introduced as "words (ABC)".
CODE_RE = re.compile(r"\b(?:[A-Z][A-Z0-9]*[0-9][A-Za-z0-9]*|[A-Z]{2,6}s?|[A-Z][A-Z0-9]*-[A-Z0-9][A-Za-z0-9]*|"
                     r"[A-Z]-[a-z]{2,})\b")
PLACEHOLDERS = {"MATH", "NUMMATH", "REF", "URL", "NAME", "AUTHORS", "CODE"}
COMMON_CODES = set("""
AI ML NLP CV LLM LM VLM MLLM RL RLHF RLAIF DPO PPO GRPO SFT KL GPU TPU CPU API CNN RNN LSTM GRU MLP
GAN VAE GPT BERT SGD ADAM ROC AUC AUROC PR CI SD SE SEM IQR ANOVA PCA SVD SVM ICA OLS MLE MAP
USA US UK EU UN DNA RNA PCR MRI FMRI EEG ECG PDF URL HTML JSON CSV ID IID OOD MSE MAE RMSE BLEU
ROUGE F1 TF IDF QA COVID WHO NIH NSF OK MNIST CIFAR COCO GLUE SQUAD MMLU GSM8K IMDB SST WMT ARC
A100 H100 V100 FLOP FLOPS TB GB MB KB CUDA LORA PEFT RAG CoT NB TODO
""".split())
SMALL_WORDS = {"of", "the", "and", "for", "in", "on", "to", "a", "an", "with", "by"}
STRESS_WORDS = set("""
not only all any every each no none never always should must could would might may can will
before after same different more less most least is are was were be been has have had do does
did this that these those it its we our they their both either neither also even still very
""".split())
NUM_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9.])[\u2212+\-]?\d+(?:[.,]\d+)*(?:/\d+)?%?")
METHODS_RE = re.compile(r"method|set-?up|materials|implementation|experimental (?:design|setting|protocol)|"
                        r"procedure|datasets?|data and|training|protocol|approach", re.I)


# --------------------------------------------------------------------------
# analysis
# --------------------------------------------------------------------------

class Finding:
    __slots__ = ("rule", "line", "section", "msg", "snippet")

    def __init__(self, rule, line, section, msg, snippet=""):
        self.rule, self.line, self.section, self.msg = rule, line, section, msg
        self.snippet = collapse(snippet)[:110]

    def as_dict(self):
        return {"rule": self.rule, "line": self.line, "section": self.section, "message": self.msg,
                "snippet": self.snippet}


def section_of(headings, appendix_line, line):
    """Top-level section name for a line, with an appendix flag."""
    name, app = "(front matter)", False
    for ln, lv, title in headings:
        if lv != 1:
            continue
        if ln <= line:
            name = title or "(untitled)"
            app = appendix_line is not None and ln >= appendix_line
        else:
            break
    return name, app


def code_key(tok):
    """Normalised form for the common-code list: upper case, plural s dropped."""
    k = tok.upper()
    return k[:-1] if len(k) > 2 and k.endswith("S") and tok[-1] == "s" else k


def is_expanded(code, before):
    """True if `before` ends with words whose initials spell `code`, as in
    'expected calibration error (' followed by 'ECE'."""
    letters = code[:-1] if code.endswith("s") else code
    if not letters.isalpha():
        return False
    initials = []
    for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", before)[-(len(letters) + 4):]:
        for part in w.split("-"):
            if part.lower() not in SMALL_WORDS:
                initials.append(part[0].upper())
    return "".join(initials[-len(letters):]) == letters.upper()


def phrase_re(phrase):
    body = r"\s+".join(re.escape(w) for w in phrase.split())
    return re.compile(r"(?<![A-Za-z])" + body + r"(?:s|es)?(?![A-Za-z])", re.I)


def reader_load(paras, emph, args):
    """M11: the names and codes a reader must carry through the main text.
    Returns (findings, inventory)."""
    acad = args.academic
    allowed = {code_key(t.strip()) for t in (args.allow_terms or "").split(",") if t.strip()}
    main = [p for p in paras if p.kind == "body" and not p.appendix]
    findings = []

    codes = {}
    for p in main:
        for m in CODE_RE.finditer(p.text):
            tok = m.group(0)
            key = code_key(tok)
            if (tok in PLACEHOLDERS or key in COMMON_CODES or key in allowed
                    or re.fullmatch(r"[IVX]+", tok)):
                continue
            c = codes.setdefault(tok, {"uses": 0, "first_line": p.line_at(m.start()), "section": p.section,
                                       "expanded": False, "paras": set()})
            c["uses"] += 1
            c["paras"].add(id(p))
            before = p.text[:m.start()].rstrip()
            if before.endswith("(") and is_expanded(tok, before[:-1]):
                c["expanded"] = True

    first_emph = {}
    for ln, phrase in emph:
        words = phrase.split()
        if all(w in STRESS_WORDS for w in words) or code_key(phrase) in allowed:
            continue
        if phrase not in first_emph or ln < first_emph[phrase]:
            first_emph[phrase] = ln
    coined = {}
    for phrase, eln in first_emph.items():
        rx = phrase_re(phrase)
        uses, first, paras_with = 0, None, set()
        for p in main:
            for m in rx.finditer(p.text):
                uses += 1
                paras_with.add(id(p))
                ln = p.line_at(m.start())
                if p.section.lower().startswith("abstract"):
                    continue
                if first is None or ln < first[0]:
                    first = (ln, p.section)
        # a coined name is italicised where the body first uses it (the abstract often uses
        # it earlier, undefined) and is then reused
        if first and first[0] == eln and uses >= 3:
            coined[phrase] = {"uses": uses, "first_line": eln, "section": first[1], "paras": paras_with}

    labels = {t: c for t, c in codes.items() if not c["expanded"]}
    acronyms = {t: c for t, c in codes.items() if c["expanded"] and c["uses"] >= 2}
    for tok, c in sorted(labels.items(), key=lambda kv: -kv[1]["uses"]):
        findings.append(Finding("M11", c["first_line"], c["section"],
                                "label code '%s' used %d time(s) and never spelled out; name the thing in "
                                "words (or pass --allow-terms if it is standard in the field)" % (tok, c["uses"]),
                                ""))
    load = sorted(coined) + sorted(acronyms)
    if len(load) > args.term_budget:
        findings.append(Finding("M11", 0, "(document)",
                                "%d coined names and acronyms to remember (budget %d): %s; replace all but the "
                                "few the argument needs with plain descriptions" %
                                (len(load), args.term_budget, ", ".join(load)), ""))
    soup_lim = 5 if acad else 4
    for p in main:
        present = [t for t, c in codes.items() if id(p) in c["paras"]]
        present += [t for t, c in coined.items() if id(p) in c["paras"]]
        if len(present) >= soup_lim:
            findings.append(Finding("M11", p.start_line, p.section,
                                    "%d names or codes in one paragraph (%s); the reader has to translate "
                                    "before reading" % (len(present), ", ".join(sorted(present))), p.text))

    def rows(d):
        return [{"term": t, "uses": c["uses"], "first_line": c["first_line"]}
                for t, c in sorted(d.items(), key=lambda kv: kv[1]["first_line"])]
    inventory = {"coined_names": rows(coined), "label_codes": rows(labels), "acronyms": rows(acronyms),
                 "term_budget": args.term_budget, "load": len(load)}
    return findings, inventory


INDEX_RE = re.compile(r"\b(?:layers?|heads?|seeds?|epochs?|steps?|tables?|figures?|figs?\.|sections?|"
                      r"appendix|eqs?\.|equations?|rows?|columns?|lines?)\s+\d{1,3}\b"
                      r"|\b\d{2}\s*%\s*(?:CI|confidence|credible)", re.I)


def count_numbers(s):
    """Numbers a reader must hold: values, not indices (layer 6, Table 2) or the CI level."""
    s = INDEX_RE.sub(" ", s)
    return len(NUM_TOKEN_RE.findall(s)) + s.count("NUMMATH")


CONTRIB_RE = re.compile(r"contribut|we (?:make|offer|provide|present) the following|in summary, we", re.I)


def list_findings(paras, lists, headings, appendix_line, args):
    """M13: lists used where the text needed an argument."""
    findings = []
    list_words = defaultdict(int)
    for start, end, counts, lead in lists:
        sec, app = section_of(headings, appendix_line, start)
        if app or (args.academic and METHODS_RE.search(sec)):
            continue
        list_words[sec] += sum(counts)
        if CONTRIB_RE.search(lead[-200:]):
            continue
        if len(counts) >= 3 and statistics.median(counts) < 12:
            findings.append(Finding("M13", start, sec,
                                    "list of %d short fragments (median %d words); if the items depend on each other, "
                                    "write prose that says how, and say what the list adds up to" %
                                    (len(counts), statistics.median(counts)), ""))
    prose_words = defaultdict(int)
    for p in paras:
        if p.kind == "body":
            prose_words[p.section] += len(words_of(p.text))
    for sec, lw in list_words.items():
        total = prose_words.get(sec, 0)
        if total >= 80 and lw / total > 0.4:
            findings.append(Finding("M13", 0, sec,
                                    "%d%% of this section's words are list items; a paper argues in paragraphs" %
                                    round(100.0 * lw / total), ""))
    return findings


def analyse(text, headings, captions, appendix_line, args, extras=None):
    extras = extras or {}
    emph = extras.get("emph", [])
    paras = build_paragraphs(text)
    for p in paras:
        p.section, app = section_of(headings, appendix_line, p.start_line)
        p.protected = args.academic and (bool(METHODS_RE.search(p.section)) or app)
        p.appendix = app
    for ln, ctext in captions:
        p = Para("caption")
        p.lines = [(ln, collapse(ctext))]
        p.finish()
        p.section, app = section_of(headings, appendix_line, ln)
        p.protected = args.academic
        p.appendix = app
        paras.append(p)
    paras = [p for p in paras if re.search(r"[A-Za-z]", p.text.replace(CITE_P, ""))]
    paras.sort(key=lambda p: p.start_line)

    findings = []
    sec_stats = defaultdict(lambda: {"paras": 0, "sentences": 0, "lengths": [], "passive": 0, "em": 0,
                                     "protected": False})
    para_dashes = []
    all_lengths = []
    roadmap_hits = []
    recent_years = []
    conn_flags = []
    cap_dash = args.max_dashes
    acad = args.academic
    body_paras = [p for p in paras if p.kind == "body"]

    for p in paras:
        st = sec_stats[p.section]
        if p.kind == "body":
            st["protected"] = st["protected"] or p.protected
        sents = split_sentences(p.text)
        is_abs = p.section.lower().startswith("abstract")

        # M1 em dashes
        ndash = p.text.count(EM)
        st["em"] += ndash
        if ndash:
            para_dashes.append((p.start_line, p.end_line, p.section, ndash, p.kind, collapse(p.text)[:70]))
            if is_abs:
                findings.append(Finding("M1", p.start_line, p.section,
                                        "%d em dash(es) in the abstract; use commas, colons or two sentences" % ndash,
                                        p.text))
            elif ndash > cap_dash and p.kind == "body":
                findings.append(Finding("M1", p.start_line, p.section,
                                        "%d em dashes in one paragraph (cap %d); keep the one that earns its place" %
                                        (ndash, cap_dash), p.text))

        # M2 pompous words
        for m in HARD_RE.finditer(p.text):
            findings.append(Finding("M2", p.line_at(m.start()), p.section,
                                    "pompous word '%s'; say the plain thing" % m.group(0), p.text[max(0, m.start() - 40):m.end() + 40]))
        soft = {m.group(0).lower() for m in SOFT_RE.finditer(p.text)}
        if len(soft) >= 3:
            findings.append(Finding("M2", p.start_line, p.section,
                                    "cluster of %d soft AI-flavoured words: %s" % (len(soft), ", ".join(sorted(soft))),
                                    p.text))

        # M4 hype (paragraph scan)
        for m in HYPE_RE.finditer(p.text):
            findings.append(Finding("M4", p.line_at(m.start()), p.section,
                                    "hype word '%s'; report the number instead" % m.group(0),
                                    p.text[max(0, m.start() - 40):m.end() + 40]))

        if p.kind != "body":
            continue
        st["paras"] += 1
        first_words = []
        triads = 0
        riders2 = 0
        para_nums = 0
        sent_lim = 6 if acad else 5
        for off, sent in sents:
            s = collapse(sent)
            ln = p.line_at(off)
            sl = s.lower().lstrip("\"'(")
            wl = words_of(s)
            first_words.append(wl[0].lower() if wl else "")
            if len(wl) >= 3:
                st["sentences"] += 1
                st["lengths"].append(len(wl))
                all_lengths.append(len(wl))
            # M3
            if THROAT_RE.match(sl):
                findings.append(Finding("M3", ln, p.section, "throat-clearing opener; start with the claim", s))
            if ROADMAP_RE.search(s):
                roadmap_hits.append((ln, p.section, s))
            if sl.startswith("in recent years"):
                recent_years.append((ln, p.section, s))
            if VAGUE_RE.search(s) and CITE_P not in s and AUTH not in s:
                findings.append(Finding("M3", ln, p.section,
                                        "vague attribution with no citation in the sentence", s))
            # M4 significance without a test
            if SIGNIF_RE.search(s) and not TEST_RE.search(s):
                findings.append(Finding("M4", ln, p.section,
                                        "'significant(ly)' with no test or interval in the sentence; use 'large' or cite the test",
                                        s))
            # M5 stacked hedges
            hedges = [h.group(0).lower() for h in HEDGE_RE.finditer(s)]
            if len(hedges) >= 2:
                findings.append(Finding("M5", ln, p.section,
                                        "stacked hedges (%s); keep each only if it qualifies a different claim" %
                                        ", ".join(hedges), s))
            # M8 triads
            for tm in TRIAD_RE.finditer(sl):
                items = tm.groups()
                if not any(i in ("math", "nummath", "ref", "url", "authors", "name") for i in items):
                    triads += 1
            # M9
            if NOT_JUST_RE.search(s) or (not acad and NOT_ONLY_RE.search(s)):
                findings.append(Finding("M9", ln, p.section, "'not just X but Y' staging; state Y", s))
            if COPULA_RE.search(s):
                findings.append(Finding("M9", ln, p.section,
                                        "copula avoidance or inflated role phrase; use 'is' or name the role", s))
            for rm in RIDER1_RE.finditer(s):
                findings.append(Finding("M9", ln, p.section,
                                        "inflated -ing rider (%s); cut it or make it a claim with evidence" %
                                        rm.group(0).strip(", "), s))
            riders2 += len(RIDER2_RE.findall(s))
            # M12 numbers per sentence
            nn = count_numbers(s)
            para_nums += nn
            if nn >= sent_lim and not p.protected:
                findings.append(Finding("M12", ln, p.section,
                                        "%d numbers in one sentence; keep the one or two that carry the claim, "
                                        "say in words what they show, move the rest to a table" % nn, s))
            # M10 passive
            pm = PASSIVE_RE.search(s)
            if pm and pm.group(1).lower() not in NOT_PARTICIPLE:
                st["passive"] += 1
                if not p.protected:
                    findings.append(Finding("M10", ln, p.section, "passive voice", s))
        # paragraph-level rules
        para_lim = 15 if acad else 12
        if para_nums >= para_lim and not p.protected:
            findings.append(Finding("M12", p.start_line, p.section,
                                    "%d numbers in one paragraph; a reader cannot hold them, so state the finding "
                                    "in words and move the values to a table" % para_nums, p.text))
        if triads >= (3 if acad else 2):
            findings.append(Finding("M8", p.start_line, p.section,
                                    "%d single-word triads in one paragraph" % triads, p.text))
        if riders2 >= 2:
            findings.append(Finding("M9", p.start_line, p.section,
                                    "%d -ing riders (demonstrating, revealing, ...) in one paragraph" % riders2, p.text))
        # M6 same-opener runs
        run_lim = 4 if acad else 3
        i = 0
        while i < len(first_words):
            j = i
            while j + 1 < len(first_words) and first_words[j + 1] == first_words[i] and first_words[i]:
                j += 1
            n = j - i + 1
            lim = run_lim + 1 if first_words[i] in ("we", "our", "the", "this") and acad else run_lim
            if n >= lim:
                findings.append(Finding("M6", p.line_at(sents[i][0]), p.section,
                                        "%d consecutive sentences open with '%s'" % (n, first_words[i]), p.text))
            i = j + 1
        first = collapse(p.text)
        conn_flags.append((p, bool(CONNECTIVE_RE.match(first))))

    # M6 connective-led paragraph runs
    thresh = 0.5 if acad else 0.3
    n_conn = sum(1 for _, c in conn_flags if c)
    if conn_flags and len(conn_flags) >= 6 and n_conn / len(conn_flags) > thresh:
        findings.append(Finding("M6", conn_flags[0][0].start_line, "(document)",
                                "%d of %d paragraphs open with a connective (cap %d%%)" %
                                (n_conn, len(conn_flags), int(thresh * 100)), ""))
    run = []
    for p, c in conn_flags + [(None, False)]:
        if c:
            run.append(p)
        else:
            if len(run) >= 3:
                findings.append(Finding("M6", run[0].start_line, run[0].section,
                                        "%d consecutive paragraphs open with a connective" % len(run), run[0].text))
            run = []

    allowed_roadmap = 1 if acad else 0
    for ln, sec, s in roadmap_hits[allowed_roadmap:]:
        findings.append(Finding("M3", ln, sec, "extra roadmap sentence (one is allowed in the introduction)", s))
    for ln, sec, s in recent_years[1:]:
        findings.append(Finding("M3", ln, sec, "'In recent years' opener used more than once", s))

    # M7 uniform sentence length
    cv_floor = 0.30 if acad else 0.35
    for name, st in sec_stats.items():
        L = st["lengths"]
        if len(L) >= 8 and statistics.mean(L) > 0:
            cv = statistics.pstdev(L) / statistics.mean(L)
            st["cv"] = cv
            if cv < cv_floor and not st["protected"]:
                findings.append(Finding("M7", 0, name,
                                        "uniform sentence length (CV %.2f < %.2f over %d sentences); vary the rhythm" %
                                        (cv, cv_floor, len(L)), ""))
        elif len(L) >= 2:
            st["cv"] = statistics.pstdev(L) / statistics.mean(L)
    load_findings, inventory = reader_load(paras, emph, args)
    findings.extend(load_findings)
    findings.extend(list_findings(paras, extras.get("lists", []), headings, appendix_line, args))
    return paras, findings, sec_stats, para_dashes, all_lengths, inventory


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------

def stats_of(L):
    if not L:
        return 0.0, 0.0, 0.0
    m = statistics.mean(L)
    sd = statistics.pstdev(L)
    return m, sd, (sd / m if m else 0.0)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Mechanical prose gate for LaTeX, Markdown or text drafts. Advisory: prints findings "
                    "with rule ids M1..M13 and line numbers; exits 0 unless the file cannot be read.",
        epilog="Rules: M1 em dashes, M2 pompous words, M3 throat-clearing and vague attribution, M4 hype and "
               "unsupported 'significant', M5 stacked hedges, M6 repeated openers, M7 uniform sentence length, "
               "M8 triads, M9 staging tells, M10 passive voice, M11 reader load (codes and coined names), "
               "M12 number density, M13 lists standing in for an argument.")
    ap.add_argument("file", help="path to a .tex, .md or .txt file")
    ap.add_argument("--academic", action="store_true",
                    help="academic exemptions: passive in Methods/appendix, one roadmap, looser thresholds")
    ap.add_argument("--format", choices=["auto", "latex", "markdown", "text"], default="auto")
    ap.add_argument("--max-dashes", type=int, default=1, help="em dashes allowed per body paragraph (default 1)")
    ap.add_argument("--max-per-rule", type=int, default=12, help="findings printed per rule (default 12)")
    ap.add_argument("--all", action="store_true", help="print every finding")
    ap.add_argument("--show-passive", action="store_true", help="also list passive sentences in protected sections")
    ap.add_argument("--term-budget", type=int, default=4,
                    help="coined names plus acronyms a reader is asked to remember in the main text (default 4)")
    ap.add_argument("--allow-terms", default="",
                    help="comma-separated codes or names that are standard in the field and need no rewording")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of the text report")
    ap.add_argument("--fail-on-findings", action="store_true", help="exit 1 if any finding remains (for CI use)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    try:
        with open(args.file, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError as e:
        print("ERROR: cannot read %s: %s" % (args.file, e), file=sys.stderr)
        return 2

    fmt = args.format
    if fmt == "auto":
        low = args.file.lower()
        if low.endswith(".tex") or "\\begin{" in raw or "\\section{" in raw:
            fmt = "latex"
        elif low.endswith((".md", ".markdown")):
            fmt = "markdown"
        else:
            fmt = "markdown"
    if fmt == "latex":
        text, headings, captions, appendix_line, extras = clean_latex(raw)
    else:
        text, headings, captions, appendix_line, extras = clean_markdown(raw)

    paras, findings, sec_stats, para_dashes, all_lengths, inventory = analyse(
        text, headings, captions, appendix_line, args, extras)
    if not args.show_passive:
        findings = [f for f in findings if not (f.rule == "M10" and sec_stats[f.section]["protected"])]
    # passive findings only when a section's share is high
    pass_thr = 0.35 if args.academic else 0.25
    keep = []
    for f in findings:
        if f.rule == "M10":
            st = sec_stats[f.section]
            if st["sentences"] and st["passive"] / st["sentences"] <= pass_thr and not args.show_passive:
                continue
        keep.append(f)
    findings = sorted(keep, key=lambda f: (int(f.rule[1:]), f.line))

    n_words = sum(len(words_of(p.text)) for p in paras if p.kind == "body")
    n_sents = len(all_lengths)
    mean, sd, cv = stats_of(all_lengths)
    counts = Counter(f.rule for f in findings)

    if args.json:
        out = {
            "file": args.file, "format": fmt, "academic": args.academic,
            "words": n_words, "paragraphs": sum(1 for p in paras if p.kind == "body"),
            "sentences": n_sents, "sentence_length_mean": round(mean, 2), "sentence_length_cv": round(cv, 3),
            "findings_by_rule": dict(counts),
            "em_dashes_per_paragraph": [
                {"lines": "%d-%d" % (a, b), "section": s, "count": c, "kind": k, "start": t}
                for a, b, s, c, k, t in para_dashes],
            "sections": {
                name: {"paragraphs": st["paras"], "sentences": st["sentences"],
                       "mean": round(stats_of(st["lengths"])[0], 2),
                       "cv": round(stats_of(st["lengths"])[2], 3),
                       "passive": st["passive"], "em_dashes": st["em"], "protected": st["protected"]}
                for name, st in sec_stats.items()},
            "reader_load": inventory,
            "findings": [f.as_dict() for f in findings],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 1 if (args.fail_on_findings and findings) else 0

    print("prose_gate: %s  (%s%s)" % (args.file, fmt, ", academic mode" if args.academic else ""))
    print("words %d | paragraphs %d | sentences %d | sentence length mean %.1f, SD %.1f, CV %.2f" %
          (n_words, sum(1 for p in paras if p.kind == "body"), n_sents, mean, sd, cv))
    names = {"M1": "em dash", "M2": "pompous words", "M3": "openers/attribution", "M4": "hype/significance",
             "M5": "stacked hedges", "M6": "repeated openers", "M7": "uniform length", "M8": "triads",
             "M9": "staging", "M10": "passive", "M11": "reader load", "M12": "number density", "M13": "lists"}
    print("findings: %d (advisory)  %s" % (len(findings),
          " | ".join("%s %s %d" % (r, names[r], counts[r]) for r in sorted(counts, key=lambda x: int(x[1:])))))
    print()
    tot_em = sum(c for _, _, _, c, k, _ in para_dashes)
    print("EM DASHES PER PARAGRAPH (cap %d per body paragraph, none in the abstract; total %d in %d paragraphs; "
          "en-dash ranges are exempt)" % (args.max_dashes, tot_em, len(para_dashes)))
    if not para_dashes:
        print("  none")
    for a, b, sec, c, kind, start in para_dashes:
        over = "  OVER CAP" if (c > args.max_dashes and kind == "body") or (sec.lower().startswith("abstract")) else ""
        label = "caption" if kind == "caption" else sec
        print("  L%d-%d [%s] %d%s: %s" % (a, b, label[:28], c, over, start))
    print()
    print("SENTENCE LENGTH AND PASSIVE VOICE BY SECTION (passive is reported, not failed, in Methods/appendix)")
    print("  %-34s %5s %5s %6s %5s %7s %6s" % ("section", "paras", "sents", "mean", "CV", "passive", "pass%"))
    for name, st in sec_stats.items():
        if not st["sentences"]:
            continue
        m, s_, c_ = stats_of(st["lengths"])
        pp = 100.0 * st["passive"] / st["sentences"]
        tag = " (protected)" if st["protected"] else ""
        print("  %-34s %5d %5d %6.1f %5.2f %7d %5.0f%%%s" %
              (name[:34], st["paras"], st["sentences"], m, c_, st["passive"], pp, tag))
    tp = sum(st["passive"] for st in sec_stats.values())
    print("  %-34s %5s %5d %6.1f %5.2f %7d %5.0f%%" %
          ("ALL", "", n_sents, mean, cv, tp, 100.0 * tp / n_sents if n_sents else 0))
    print()
    print("READER LOAD: NAMES AND CODES THE MAIN TEXT ASKS THE READER TO REMEMBER (budget %d, load %d)" %
          (inventory["term_budget"], inventory["load"]))
    for label, key in (("coined names", "coined_names"), ("acronyms", "acronyms"),
                       ("label codes, never spelled out", "label_codes")):
        items = inventory[key]
        shown_items = ", ".join("%s (%d, L%d)" % (r["term"], r["uses"], r["first_line"]) for r in items[:20])
        more = " (+%d more)" % (len(items) - 20) if len(items) > 20 else ""
        print("  %-31s %s%s" % (label + ":", shown_items or "none", more))
    print()
    print("FINDINGS")
    cur = None
    shown = 0
    for f in findings:
        if f.rule != cur:
            cur = f.rule
            shown = 0
            print("  -- %s %s" % (cur, names[cur]))
        shown += 1
        if shown > args.max_per_rule and not args.all:
            if shown == args.max_per_rule + 1:
                print("     (+%d more, rerun with --all)" % (counts[cur] - args.max_per_rule))
            continue
        loc = "L%d" % f.line if f.line else "section"
        snip = (': "%s"' % f.snippet) if f.snippet else ""
        print("     %s [%s] %s%s" % (loc, f.section[:22], f.msg, snip))
    if not findings:
        print("  none")
    return 1 if (args.fail_on_findings and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
