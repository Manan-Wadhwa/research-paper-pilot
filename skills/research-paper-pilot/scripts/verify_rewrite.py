#!/usr/bin/env python3
"""verify_rewrite.py: prove that a prose rewrite kept the facts of its source.

What it compares (each is a "fact"; losing or inventing one is a FAIL)
  numbers (with attached units such as %, GB, ms, layers), years, proper nouns and identifiers,
  citation keys (LaTeX \\cite*, Markdown [@key], numeric [12], author-year), URLs / DOIs / arXiv ids,
  quoted strings, LaTeX \\ref / \\label keys, non-trivial math spans, and custom LaTeX macros
  (for example a number macro like \\NumAcc{}).

What it only warns about (a FAIL under --strict)
  hedge families that vanish or shrink (may, suggests, probably, roughly ...), added certainty words
  (proves, clearly, always ...), a changed count of negations, repeated-number counts, and structural
  flattening: sentence-length CV or paragraph-length variation dropping sharply, or the text
  growing or shrinking by more than a third.

LaTeX awareness: comments, preamble, floats and tables are skipped; \\cite{a,b} contributes the keys a
and b as facts; $math$ is compared as a unit (simple numeric math such as $0.02\\%$ is read as text);
formatting commands are unwrapped so wording can change around them.

Usage
  python verify_rewrite.py source.md rewrite.md
  python verify_rewrite.py old.tex new.tex --strict --json

Exit codes: 0 PASS (warnings allowed), 1 FAIL (dropped or added facts, or a strict failure),
            2 an input file cannot be read. Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter

EM = "\u2014"
EN = "\u2013"
BREAK = "\x03"
CITE_P = "[@c]"
AUTH = "AUTHORS"
PLACEHOLDERS = {"MATH", "REF", "URL", "AUTHORS", "NAME", "CODE"}


# --------------------------------------------------------------------------
# helpers shared with the LaTeX cleaner
# --------------------------------------------------------------------------

def balanced(s, i):
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
    out = []
    pos = 0
    for m in pat.finditer(s):
        if m.start() < pos:
            continue
        end = balanced(s, m.end() - 1)
        if end < 0:
            continue
        out.append(s[pos:m.start()])
        out.append(fn(m, s[m.end():end - 1]))
        pos = end
    out.append(s[pos:])
    return "".join(out)


def nl(t):
    return "\n" * t.count("\n")


def line_of(m):
    return m.string.count("\n", 0, m.start()) + 1


class Facts:
    def __init__(self):
        self.items = {}   # (kind, value) -> [count, first_line]

    def add(self, kind, value, line):
        k = (kind, value)
        if k in self.items:
            self.items[k][0] += 1
        else:
            self.items[k] = [1, line]

    def kinds(self, kind):
        return {v: c[0] for (k, v), c in self.items.items() if k == kind}


FLOAT_RE = re.compile(r"\\begin\{((?:figure|table|wrapfigure|wraptable|sidewaystable|sidewaysfigure)\*?)\}(.*?)\\end\{\1\}", re.S)
CAPTION_RE = re.compile(r"\\caption(?:\[[^\]]*\])?\{")
MATH_ENV_RE = re.compile(r"\\begin\{((?:equation|align|alignat|gather|eqnarray|multline|flalign|displaymath|math)\*?)\}(.*?)\\end\{\1\}", re.S)
DROP_ENV_RE = re.compile(r"\\begin\{((?:tabular|tabularx|tabulary|longtable|array|verbatim|lstlisting|minted|thebibliography|tikzpicture|algorithm|algorithmic|comment)\*?)\}.*?\\end\{\1\}", re.S)
HEAD_RE = re.compile(r"\\(?:chapter|section|subsection|subsubsection|paragraph|subparagraph)\*?(?:\[[^\]]*\])?\{")
CITE_RE = re.compile(r"\\(cite[a-zA-Z]*|parencite|textcite|autocite|footcite|nocite)\*?((?:\[[^\]]*\])*)\{([^}]*)\}")
REF_RE = re.compile(r"\\(ref|eqref|autoref|cref|Cref|pageref|nameref|vref|label)\*?\{([^}]*)\}")
MATH_RE = re.compile(r"\$\$(.*?)\$\$|\\\[(.*?)\\\]|\\\((.*?)\\\)|\$([^$]*)\$", re.S)
FOOTNOTE_RE = re.compile(r"\\(?:footnote|thanks)\{")
NEWCMD_RE = re.compile(r"\\(?:re)?newcommand\*?\s*\{?\\[a-zA-Z]+\}?(?:\[\d\])?\{")
KNOWN = set("""
emph textbf textit texttt textsc textrm textsf text textnormal underline mbox hbox section subsection subsubsection
paragraph subparagraph chapter caption captionof item begin end footnote url href label ref eqref autoref cref Cref
pageref includegraphics centering noindent hline toprule midrule bottomrule cline newline linebreak title author date
maketitle abstract bibliography bibliographystyle input include small footnotesize large Large LARGE huge Huge
normalsize tiny scriptsize vspace hspace smallskip medskip bigskip par and left right bf it em rm sf tt sc thanks
appendix tableofcontents newpage clearpage quad qquad textwidth linewidth columnwidth ldots dots cdots LaTeX TeX
textbackslash textasciitilde textless textgreater path S P sloppy begingroup endgroup relax protect
""".split())
NUMERIC_MATH_RE = re.compile(r"^[\d\s.,%~\u2248\u2265\u2264\u00b1\u00d7<>=+\-\u2212/()]*$")


def math_to_plain(m):
    t = m
    for a, b in (("{,}", ","), ("\\%", "%"), ("\\,", ""), ("\\;", ""), ("\\!", ""), ("\\ ", ""),
                 ("{\\sim}", "~"), ("\\sim", "~"), ("\\geq", "\u2265"), ("\\ge", "\u2265"),
                 ("\\leq", "\u2264"), ("\\le", "\u2264"), ("\\pm", "\u00b1"), ("\\times", "\u00d7"),
                 ("\\approx", "\u2248"), ("{", ""), ("}", "")):
        t = t.replace(a, b)
    return t


def latex_to_text(raw, facts):
    """Strip LaTeX, recording structural facts. Returns text with placeholders."""
    s = raw.replace("\r\n", "\n")
    s = re.sub(r"(?<!\\)%.*", "", s)
    m = re.search(r"\\begin\{document\}", s)
    if m:
        s = nl(s[:m.end()]) + s[m.end():]
    m = re.search(r"\\end\{document\}", s)
    if m:
        s = s[:m.start()] + nl(s[m.start():])
    s = sub_balanced(s, NEWCMD_RE, lambda m, inner: nl(m.group(0)) + nl(inner))
    s = s.replace("\\$", "\x01").replace("\\%", "%").replace("\\&", "&").replace("\\_", "_").replace("\\#", "#")

    # floats: keep only captions (tables are not prose)

    def _captions_only(m):
        body = m.group(2)
        outs = []
        for cm in CAPTION_RE.finditer(body):
            end = balanced(body, cm.end() - 1)
            if end > 0:
                outs.append(body[cm.end():end - 1])
        keep = " ".join(outs)
        return keep + "\n" * max(0, m.group(0).count("\n") - keep.count("\n")) + BREAK
    s = FLOAT_RE.sub(lambda m: BREAK + _captions_only(m), s)

    def menv(m):
        body = m.group(2)
        for lm in re.finditer(r"\\label\{([^}]*)\}", body):
            facts.add("label", lm.group(1).strip(), line_of(m))
        body = re.sub(r"\\label\{[^}]*\}", "", body)
        facts.add("math", re.sub(r"\s+", "", body), line_of(m))
        return " MATH " + nl(m.group(0))
    s = MATH_ENV_RE.sub(menv, s)
    s = DROP_ENV_RE.sub(lambda m: BREAK + nl(m.group(0)), s)
    s = sub_balanced(s, HEAD_RE, lambda m, inner: BREAK + inner + BREAK)
    s = re.sub(r"\\item\b(?:\[[^\]]*\])?", BREAK, s)
    s = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\{[^}]*\})?(?:\[[^\]]*\])?", BREAK, s)

    def cite_cb(m):
        name = m.group(1)
        for key in m.group(3).split(","):
            key = key.strip()
            if key:
                facts.add("citation", key, line_of(m))
        if name == "nocite":
            return nl(m.group(0))
        if name.startswith(("citet", "textcite", "citeauthor", "citealt")):
            return AUTH + nl(m.group(0))
        return CITE_P + nl(m.group(0))
    s = CITE_RE.sub(cite_cb, s)

    def ref_cb(m):
        kind = "label" if m.group(1) == "label" else "ref"
        facts.add(kind, m.group(2).strip(), line_of(m))
        return ("" if kind == "label" else "REF") + nl(m.group(0))
    s = REF_RE.sub(ref_cb, s)

    def url_cb(m):
        facts.add("url", m.group(1).strip().rstrip(".,;:"), line_of(m))
        return "URL"
    s = re.sub(r"\\url\{([^}]*)\}", url_cb, s)
    s = re.sub(r"\\href\{([^}]*)\}\{([^{}]*)\}",
               lambda m: (facts.add("url", m.group(1).strip(), line_of(m)), m.group(2))[1], s)
    s = sub_balanced(s, FOOTNOTE_RE, lambda m, inner: nl(inner))

    def math_cb(m):
        inner = next(g for g in m.groups() if g is not None)
        plain = math_to_plain(inner)
        if NUMERIC_MATH_RE.match(plain):
            return " " + plain + " " + nl(m.group(0))
        facts.add("math", re.sub(r"\s+", "", inner), line_of(m))
        return " MATH " + nl(m.group(0))
    s = MATH_RE.sub(math_cb, s)

    def macro_cb(m):
        name = m.group(1)
        if name not in KNOWN:
            facts.add("macro", "\\" + name, line_of(m))
        return m.group(0)
    re.sub(r"\\([A-Za-z]+)", macro_cb, s)
    s = re.sub(r"\\(?:includegraphics|input|include|bibliography|bibliographystyle|vspace|hspace|setlength|"
               r"usepackage)\*?(?:\[[^\]]*\])*(?:\{[^{}]*\})*", "", s)
    s = re.sub(r"\\[a-zA-Z]+\*?\{\}", " NAME ", s)
    for _ in range(8):
        new = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", s)
        if new == s:
            break
        s = new
    s = re.sub(r"\\[a-zA-Z]+\*?", "", s)
    s = re.sub(r"\\\\(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\[,;:! @\-]", " ", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ")
    s = s.replace("``", '"').replace("''", '"')
    s = s.replace("---", EM).replace(" -- ", " " + EM + " ")
    s = re.sub(r"(?<=\w)--(?=\w)", EN, s)
    s = s.replace("\x01", "$")
    return s


def markdown_to_text(raw, facts):
    s = raw.replace("\r\n", "\n")
    lines = s.split("\n")
    if lines and lines[0].strip() == "---":
        for k in range(1, min(len(lines), 60)):
            if lines[k].strip() in ("---", "..."):
                for j in range(0, k + 1):
                    lines[j] = ""
                break
    out = []
    in_code = False
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            in_code = not in_code
            out.append(BREAK)
            continue
        if in_code:
            out.append("")
            continue
        line = re.sub(r"^(#{1,6})\s+(.*?)\s*#*\s*$", lambda m: BREAK + m.group(2) + BREAK, line)
        if line.lstrip().startswith("|") or re.match(r"^\s*([-*_]\s*){3,}$", line):
            out.append(BREAK)
            continue
        line = re.sub(r"^\s*>\s?", "", line)
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", BREAK, line)
        out.append(line)
    s = "\n".join(out)
    s = re.sub(r"<!--.*?-->", lambda m: nl(m.group(0)), s, flags=re.S)
    s = re.sub(r"`[^`\n]*`", "CODE", s)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)

    def link_cb(m):
        facts.add("url", m.group(2).strip().rstrip(".,;:"), line_of(m))
        return m.group(1)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]*)\)", link_cb, s)

    def key_cb(m):
        for key in re.findall(r"@([\w:.\-/]+)", m.group(0)):
            facts.add("citation", key.rstrip(".:"), line_of(m))
        return CITE_P
    s = re.sub(r"\[(?:[^\]@\n]*@[^\]]+)\]", key_cb, s)

    def num_cb(m):
        for part in re.split(r"\s*,\s*", m.group(0)[1:-1]):
            rng = re.match(r"(\d+)\s*[\u2013-]\s*(\d+)$", part)
            if rng and int(rng.group(2)) - int(rng.group(1)) < 50:
                for k in range(int(rng.group(1)), int(rng.group(2)) + 1):
                    facts.add("citation", "#%d" % k, line_of(m))
            elif part.strip().isdigit():
                facts.add("citation", "#%s" % part.strip(), line_of(m))
        return CITE_P
    s = re.sub(r"\[\d+(?:\s*[,\u2013-]\s*\d+)*\]", num_cb, s)

    def ay_cb(m):
        facts.add("citation", re.sub(r"\s+", " ", m.group(0)[1:-1]), line_of(m))
        return CITE_P
    s = re.sub(r"\((?:[A-Z][A-Za-z\-]+(?:\s+et al\.|\s+and\s+[A-Z][A-Za-z\-]+)?,?\s+\d{4}[a-z]?(?:;[^)]*)?)\)", ay_cb, s)
    # LaTeX-style commands that sometimes appear in Markdown (pandoc, Overleaf notes)
    s = CITE_RE.sub(lambda m: (
        [facts.add("citation", k.strip(), line_of(m)) for k in m.group(3).split(",") if k.strip()],
        CITE_P)[1], s)

    def mm(m):
        inner = next(g for g in m.groups() if g is not None)
        plain = math_to_plain(inner)
        if NUMERIC_MATH_RE.match(plain):
            return " " + plain + " "
        facts.add("math", re.sub(r"\s+", "", inner), line_of(m))
        return " MATH "
    s = MATH_RE.sub(mm, s)
    s = re.sub(r"(\*\*|__)(.+?)\1", r"\2", s)
    s = re.sub(r"(?<![\w*])[*_]([^*_\n]+)[*_](?![\w*])", r"\1", s)
    s = s.replace("---", EM).replace(" -- ", " " + EM + " ")
    s = re.sub(r"(?<=\w)--(?=\w)", EN, s)
    return s


# --------------------------------------------------------------------------
# number, unit, proper noun, quote extraction
# --------------------------------------------------------------------------

NUMWORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
            "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
            "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
            "thousand": 1000, "million": 1000000}
NUMWORD_RE = re.compile(r"\b(?:(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[- ](one|two|three|four|five|six|seven|eight|nine)|(" +
                        "|".join(NUMWORDS) + r"))\b", re.I)
UNIT_SYMBOLS = {"%", "ms", "s", "B", "M", "K", "KB", "MB", "GB", "TB", "GiB", "MiB", "Hz", "kHz", "MHz", "GHz",
                "kg", "g", "mg", "mm", "cm", "m", "km", "nm", "V", "W", "kW", "J", "x", "\u00d7", "\u00b0C",
                "\u00b0F", "FLOPs", "px", "dB", "ppm", "bp"}
UNIT_WORDS = {"percent", "pct", "second", "sec", "minute", "min", "hour", "hr", "day", "week", "month", "year",
              "nat", "bit", "token", "layer", "head", "neuron", "sample", "epoch", "step", "example", "parameter",
              "param", "seed", "run", "trial", "participant", "patient", "subject", "item", "pair", "prompt",
              "word", "sentence", "page", "image", "class", "batch", "iteration", "gpu", "cpu", "fold", "shot",
              "dimension", "unit", "component", "feature", "model", "arm", "cell", "site", "paper", "author",
              "annotator", "document", "question", "turn", "round", "sample", "record", "channel"}
UNIT_CANON = {"percent": "%", "pct": "%", "sec": "s", "second": "s", "minute": "min", "hour": "h", "hr": "h",
              "param": "parameter"}
UNITS_ALT = "|".join(sorted({re.escape(u) for u in UNIT_SYMBOLS if u != "%"} |
                            {re.escape(u) + "s?" for u in UNIT_WORDS}, key=len, reverse=True))
NUM_CORE = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?|\.\d+"
RANGE_RE = re.compile(r"(?<![\w.])(" + NUM_CORE + r")\s*(?:[\u2013-]|to)\s*(" + NUM_CORE + r")\s*(%|(?:" + UNITS_ALT + r")\b)", re.I)
NUM_RE = re.compile(r"(?<![\w.])(" + NUM_CORE + r")(?:[eE][-+]?\d+)?")
CAP_RE = re.compile(r"[A-Z][A-Za-z0-9]*(?:[-.](?=[A-Za-z0-9])[A-Za-z0-9]+)*(?:['\u2019]s)?")
STOP_CAPS = {"Figure", "Fig", "Table", "Section", "Sec", "Appendix", "Eq", "Equation", "Theorem", "Lemma",
             "Algorithm", "Chapter", "Proposition", "Definition", "Corollary", "Remark", "Example", "Step",
             "Part", "Panel", "I"}
ABBR_BEFORE_PERIOD = {"e.g", "i.e", "vs", "cf", "al", "fig", "eq", "sec", "no", "approx", "resp", "etc", "dr",
                      "mr", "ms", "prof", "st"}


def norm_number(txt):
    t = txt.replace(",", "")
    if t.startswith("."):
        t = "0" + t
    return t


def unit_after(text, end):
    m = re.match(r"\s{0,3}(%|percent|per cent|[\u00b0\u00d7A-Za-z]+)", text[end:end + 18])
    if not m:
        return ""
    tok = m.group(1)
    if tok == "per":
        return ""
    if tok in ("percent", "pct") or text[end:end + 9].lstrip().startswith("per cent"):
        return "%"
    if tok == "%":
        return "%"
    if tok in UNIT_SYMBOLS:
        return tok
    low = tok.lower()
    base = low[:-1] if low.endswith("s") and low[:-1] in UNIT_WORDS else low
    if base in UNIT_WORDS:
        return UNIT_CANON.get(base, base)
    return ""


def sentence_start(text, i):
    """True if the token at text[i] opens a sentence, paragraph or heading."""
    j = i - 1
    nls = 0
    while j >= 0 and (text[j] in " \t\n\"'\u201c\u2018([" or text[j] == BREAK):
        if text[j] == "\n":
            nls += 1
        if text[j] == BREAK:
            return True
        j -= 1
    if j < 0 or nls >= 2:
        return True
    if text[j] in ".!?:":
        if text[j] == ".":
            k = j - 1
            while k >= 0 and (text[k].isalpha() or text[k] == "."):
                k -= 1
            word = text[k + 1:j].lower()
            if word in ABBR_BEFORE_PERIOD:
                return False
        return True
    return False


def extract_text_facts(text, facts, caps_out):
    t = text
    # urls, dois, arxiv ids
    def url_cb(m):
        facts.add("url", m.group(0).rstrip(".,;:)"), line_of(m))
        return " URL "
    t = re.sub(r"https?://[^\s)\]>}\"']+", url_cb, t)
    t = re.sub(r"\b10\.\d{4,9}/[^\s\"<>]+", lambda m: (facts.add("url", "doi:" + m.group(0).rstrip(".,;:)"), line_of(m)), " URL ")[1], t)
    t = re.sub(r"arXiv:\s?(\d{4}\.\d{4,5})(?:v\d+)?", lambda m: (facts.add("url", "arxiv:" + m.group(1), line_of(m)), " URL ")[1], t)
    t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    for m in re.finditer(r'"([^"\n]{2,160}?)"', t):
        q = re.sub(r"\s+", " ", m.group(1)).strip()
        if q and re.search(r"[A-Za-z0-9]", q):
            facts.add("quote", q, line_of(m))
    # capitalised tokens
    for m in CAP_RE.finditer(t):
        tok = m.group(0)
        if tok.endswith("'s"):
            tok = tok[:-2]
        if tok in STOP_CAPS or tok in PLACEHOLDERS or len(tok) == 0:
            continue
        if tok in UNIT_SYMBOLS and re.search(r"\d\s{0,3}$", t[max(0, m.start() - 5):m.start()]):
            continue
        start = sentence_start(t, m.start())
        has_digit = any(c.isdigit() for c in tok)
        camel = has_digit or sum(1 for c in tok if c.isupper()) >= 2
        nxt = t[m.end():m.end() + 40]
        nextcap = bool(re.match(r"[ ][A-Z][a-z]", nxt))
        caps_out.append({"tok": tok, "line": line_of(m), "start": start, "camel": camel, "nextcap": nextcap,
                         "digit": has_digit})
    # remove identifier tokens containing digits so their digits are not read as numbers
    t2 = CAP_RE.sub(lambda m: " " if any(c.isdigit() for c in m.group(0)) else m.group(0), t)
    t2 = re.sub(r"(?<!\w)\(\d{1,2}\)(?=\s)", " ", t2)
    t2 = re.sub(r"(?m)^\s*\d{1,2}[.)]\s", " ", t2)
    t2 = re.sub(r"\[@c\]|URL|MATH|REF", " ", t2)
    # spelled numbers become digits
    def nw(m):
        if m.group(1):
            return str(NUMWORDS[m.group(1).lower()] + NUMWORDS[m.group(2).lower()])
        return str(NUMWORDS[m.group(3).lower()])
    t2 = NUMWORD_RE.sub(nw, t2)
    # ranges with units: "78-107%" -> "78 % 107 %"
    t2 = RANGE_RE.sub(lambda m: "%s %s %s %s" % (m.group(1), m.group(3), m.group(2), m.group(3)), t2)
    for m in NUM_RE.finditer(t2):
        raw = m.group(1)
        val = norm_number(raw)
        pre = t2[max(0, m.start() - 2):m.start()]
        sign = ""
        if pre.endswith(("-", "\u2212")) and (len(pre) < 2 or pre[0] in " (\n"):
            sign = "-"
        unit = unit_after(t2, m.end())
        full = sign + val
        if unit:
            facts.add("number", "%s %s" % (full, unit), line_of(m))
        elif re.fullmatch(r"(?:19|20)\d\d", val):
            facts.add("year", val, line_of(m))
        else:
            facts.add("number", full, line_of(m))
    return t


# --------------------------------------------------------------------------
# hedges, strengtheners, negations
# --------------------------------------------------------------------------

HEDGE_FAMILIES = {
    "modal (may/might/could)": r"\b(?:may|might|could)\b",
    "hedging verb (suggest/appear/seem/tend/indicate)": r"\b(?:suggest(?:s|ed|ing)?|appear(?:s|ed|ing)?|seem(?:s|ed|ing)?|tend(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|hypothesi[sz]e[sd]?|speculat\w*)\b",
    "probability adverb (possibly/probably/likely/...)": r"\b(?:possibly|perhaps|potentially|probably|likely|presumably|arguably|seemingly|plausibly|conceivably)\b",
    "approximation (roughly/approximately/~)": r"\b(?:roughly|approximately|nearly|almost)\b|[~\u2248]",
    "degree (somewhat/relatively/partly)": r"\b(?:somewhat|relatively|fairly|partly|partially)\b",
    "caveat (preliminary/tentative)": r"\b(?:preliminary|tentative(?:ly)?|provisional(?:ly)?|exploratory)\b",
}
STRENGTH_RE = re.compile(r"\b(?:proves?|proven|demonstrates?|demonstrated|clearly|definitively|always|never|entirely|"
                         r"consistently|undoubtedly|obviously|certainly|confirms?|confirmed|establishes?|established|"
                         r"causes?|conclusively|unambiguously)\b", re.I)
NEG_RE = re.compile(r"\b(?:not|no|never|neither|nor|cannot|without|none|fails? to)\b|n't|n\u2019t", re.I)


# --------------------------------------------------------------------------
# sentences and structure
# --------------------------------------------------------------------------

ABBR = ["e.g.", "i.e.", "et al.", "vs.", "cf.", "Fig.", "Figs.", "Eq.", "Eqs.", "Sec.", "Ref.", "No.", "approx.",
        "resp.", "etc.", "Dr.", "Mr.", "Ms.", "Prof.", "St."]
SPLIT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"')\]]))\s+(?=[\"'(\[]?[A-Z0-9\[])")
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\u2019\-./%][A-Za-z0-9]+)*%?")


def sentences_of(par):
    t = par
    for a in ABBR:
        t = t.replace(a, a.replace(".", "\x02"))
    return [x.replace("\x02", ".") for x in SPLIT_RE.split(t) if x.strip()]


def nwords(s):
    return len(WORD_RE.findall(s.replace(CITE_P, " ")))


def structure(text):
    paras = [p for p in re.split(r"\n\s*\n|" + BREAK, text) if p.strip()]
    paras = [re.sub(r"\s+", " ", p).strip() for p in paras]
    paras = [p for p in paras if nwords(p) >= 4]
    sent_len = []
    for p in paras:
        for s in sentences_of(p):
            n = nwords(s)
            if n >= 3:
                sent_len.append(n)
    plen = [nwords(p) for p in paras]

    def cv(L):
        if len(L) < 2:
            return None
        m = statistics.mean(L)
        return statistics.pstdev(L) / m if m else None
    return {"paragraphs": len(paras), "sentences": len(sent_len), "words": sum(plen),
            "sent_mean": round(statistics.mean(sent_len), 2) if sent_len else 0.0,
            "sent_sd": round(statistics.pstdev(sent_len), 2) if len(sent_len) > 1 else 0.0,
            "sent_cv": round(cv(sent_len), 3) if cv(sent_len) is not None else None,
            "para_cv": round(cv(plen), 3) if cv(plen) is not None else None}


# --------------------------------------------------------------------------
# load and compare
# --------------------------------------------------------------------------

class Doc:
    def __init__(self, path, fmt):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        if fmt == "auto":
            low = path.lower()
            fmt = "latex" if (low.endswith(".tex") or "\\begin{" in raw or "\\cite" in raw or "\\section{" in raw) else "markdown"
        self.path, self.fmt = path, fmt
        self.facts = Facts()
        text = latex_to_text(raw, self.facts) if fmt == "latex" else markdown_to_text(raw, self.facts)
        self.caps = []
        self.text = extract_text_facts(text, self.facts, self.caps)
        low = self.text.lower()
        self.hedges = {k: len(re.findall(v, low)) for k, v in HEDGE_FAMILIES.items()}
        self.strength = Counter(m.group(0).lower() for m in STRENGTH_RE.finditer(self.text))
        self.neg = len(NEG_RE.findall(self.text))
        self.struct = structure(self.text)


def finalize_proper_nouns(docs):
    mid = set()
    for d in docs:
        for c in d.caps:
            if not c["start"]:
                mid.add(c["tok"])
    for d in docs:
        for c in d.caps:
            tok = c["tok"]
            ok = (not c["start"]) or c["camel"] or tok in mid or c["nextcap"]
            if tok == "A" and c["start"]:
                ok = False
            if ok:
                d.facts.add("proper noun", tok, c["line"])


KIND_ORDER = ["number", "year", "proper noun", "citation", "url", "quote", "ref", "label", "math", "macro"]


def compare(src, new, strict):
    dropped, added, warns = [], [], []
    for kind in KIND_ORDER:
        a, b = src.facts.kinds(kind), new.facts.kinds(kind)
        for v in sorted(set(a) - set(b)):
            dropped.append({"kind": kind, "value": v, "line": src.facts.items[(kind, v)][1]})
        for v in sorted(set(b) - set(a)):
            added.append({"kind": kind, "value": v, "line": new.facts.items[(kind, v)][1]})
        if kind in ("number", "year", "citation"):
            for v in sorted(set(a) & set(b)):
                if a[v] != b[v]:
                    msg = "%s %r appears %d time(s) in source, %d in rewrite" % (kind, v, a[v], b[v])
                    warns.append({"type": "count", "msg": msg, "strict_fail": True})
    for fam in HEDGE_FAMILIES:
        s, n = src.hedges[fam], new.hedges[fam]
        if s and n == 0:
            warns.append({"type": "hedge", "msg": "hedge family vanished: %s (source %d, rewrite 0). Restore it "
                          "if it qualified a claim" % (fam, s), "strict_fail": True})
        elif s and n < s:
            warns.append({"type": "hedge", "msg": "hedge family reduced: %s (source %d, rewrite %d). Fine if "
                          "they were stacked on one claim" % (fam, s, n), "strict_fail": False})
        elif n > s:
            warns.append({"type": "hedge", "msg": "hedge family added: %s (source %d, rewrite %d)" % (fam, s, n),
                          "strict_fail": False})
    for w, c in new.strength.items():
        if c > src.strength.get(w, 0):
            warns.append({"type": "strength", "msg": "certainty word added or repeated: '%s' (source %d, rewrite %d); "
                          "check the claim is not stronger now" % (w, src.strength.get(w, 0), c),
                          "strict_fail": False})
    if src.neg != new.neg:
        warns.append({"type": "negation", "msg": "negation count changed %d -> %d; check no claim flipped or scope shifted"
                      % (src.neg, new.neg), "strict_fail": True})
    # structure
    a, b = src.struct, new.struct
    sflag = []
    if a["words"] and (b["words"] > a["words"] * 1.34 or b["words"] < a["words"] * 0.66):
        sflag.append("word count changed %d -> %d (more than a third)" % (a["words"], b["words"]))
    if a["sent_cv"] is not None and b["sent_cv"] is not None and a["sentences"] >= 5 and b["sentences"] >= 5:
        if b["sent_cv"] < a["sent_cv"] - 0.10 and b["sent_cv"] < 0.40:
            sflag.append("sentence-length CV flattened %.2f -> %.2f; vary the rhythm again" % (a["sent_cv"], b["sent_cv"]))
    if a["para_cv"] is not None and b["para_cv"] is not None and a["paragraphs"] >= 3 and b["paragraphs"] >= 3:
        if a["para_cv"] > 0.15 and b["para_cv"] < a["para_cv"] * 0.6:
            sflag.append("paragraph-length variation flattened %.2f -> %.2f" % (a["para_cv"], b["para_cv"]))
    return dropped, added, warns, sflag


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Check that a rewrite kept every fact of its source: numbers and units, years, proper "
                    "nouns, citation keys, URLs, quotes, LaTeX refs, math and macros. DROPPED or ADDED facts "
                    "FAIL. Hedges, negations and rhythm produce warnings (failures with --strict).",
        epilog="Exit codes: 0 PASS, 1 FAIL, 2 unreadable input.")
    ap.add_argument("source", help="the original text (.tex, .md, .txt)")
    ap.add_argument("rewrite", help="the rewritten text")
    ap.add_argument("--strict", action="store_true",
                    help="also fail on vanished hedge families, changed negation count, changed repeat counts "
                         "of numbers/citations, and structural flattening")
    ap.add_argument("--format", choices=["auto", "latex", "markdown", "text"], default="auto",
                    help="parse both files as this format (default: detect per file)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of the text report")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    fmt = "markdown" if args.format == "text" else args.format
    try:
        src = Doc(args.source, fmt)
        new = Doc(args.rewrite, fmt)
    except OSError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    finalize_proper_nouns([src, new])
    dropped, added, warns, sflag = compare(src, new, args.strict)
    strict_fail = args.strict and (any(w["strict_fail"] for w in warns) or bool(sflag))
    failed = bool(dropped or added or strict_fail)
    n_warn = len(warns) + len(sflag)
    result = "FAIL" if failed else "PASS"

    if args.json:
        print(json.dumps({
            "result": result, "strict": args.strict, "source": args.source, "rewrite": args.rewrite,
            "formats": [src.fmt, new.fmt], "dropped": dropped, "added": added,
            "warnings": [w["msg"] for w in warns] + sflag,
            "structure": {"source": src.struct, "rewrite": new.struct},
            "fact_counts": {k: len(src.facts.kinds(k)) for k in KIND_ORDER}}, indent=2, ensure_ascii=False))
        return 1 if failed else 0

    print("verify_rewrite: %s  vs  %s  (%s / %s%s)" % (args.source, args.rewrite, src.fmt, new.fmt,
                                                       ", strict" if args.strict else ""))
    print("RESULT: %s  (%d dropped, %d added, %d warnings)" % (result, len(dropped), len(added), n_warn))
    counts = {k: len(src.facts.kinds(k)) for k in KIND_ORDER}
    print("facts in source: " + ", ".join("%d %s" % (v, k) for k, v in counts.items() if v))
    for d in dropped:
        print("DROPPED %-11s %r  (source line %d)" % (d["kind"], d["value"], d["line"]))
    for a in added:
        print("ADDED   %-11s %r  (rewrite line %d)" % (a["kind"], a["value"], a["line"]))
    for w in warns:
        print("WARN %s%s" % (w["msg"], " [strict: fail]" if (args.strict and w["strict_fail"]) else ""))
    for f in sflag:
        print("WARN structure: %s%s" % (f, " [strict: fail]" if args.strict else ""))
    a, b = src.struct, new.struct
    print("structure: sentences %d -> %d | sentence mean %.1f -> %.1f | sentence CV %s -> %s | paragraphs %d -> %d | "
          "paragraph CV %s -> %s | words %d -> %d" %
          (a["sentences"], b["sentences"], a["sent_mean"], b["sent_mean"], a["sent_cv"], b["sent_cv"],
           a["paragraphs"], b["paragraphs"], a["para_cv"], b["para_cv"], a["words"], b["words"]))
    if failed:
        print("Fix the DROPPED and ADDED lines (restore what was lost, remove what was invented), then rerun.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
