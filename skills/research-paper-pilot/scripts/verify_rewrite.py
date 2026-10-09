#!/usr/bin/env python3
"""verify_rewrite.py: prove that a prose rewrite kept the facts of its source.

What it compares (each is a "fact"; losing or inventing one is a FAIL)
  numbers (with attached units such as %, GB, ms, layers; exponents kept, so 3e-4, 3E-4,
  3 x 10^-4 and $3\\times10^{-4}$ are one value and 3e-5 is another; spelled numbers such as
  "two hundred" or "one seed" read as digits), years, proper nouns and identifiers, citation keys
  (LaTeX \\cite*, Markdown [@key], numeric [12], author-year in either "(Smith et al., 2020)" or
  "Smith et al. (2020)" form), URLs / DOIs / arXiv ids, quoted strings, LaTeX \\ref / \\label keys,
  non-trivial math spans, and custom LaTeX macros (for example a number macro like \\NumAcc{}).

Claim markers (also a FAIL by default)
  Each sentence is cut into clauses and anchored to its facts (numbers, proper nouns) and content
  words; each clause is matched to the rewrite clauses that share most of those anchors. A negation
  (not, no, never, none, fails to, rather than ...; "without" only counts toward the overall negation
  count, since "removing X" -> "without X" is a paraphrase) or a meaning-bearing hedge (may, might,
  suggests, seems, likely, possibly, roughly ...) that is present in a source clause and absent from
  every matching rewrite clause is reported as DROPPED with its sentence; one that appears in a
  rewrite clause with no counterpart in the matching source clauses is ADDED. So "not significant" -> "significant",
  "may reflect" -> "reflects", and a "not" moved from the layer-9 claim to the layer-6 claim all fail.
  Qualifiers fixed to a number are compared per number: approximators (about, approximately, roughly,
  around, nearly, ~) and bounds (more than, at least, up to, <, >=, ...): "about 12%" -> "12%" fails.
  --lenient-hedges / --lenient-negations turn those failures into warnings (failures under --strict).

What it only warns about (a FAIL under --strict)
  hedge families that vanish or shrink overall, added certainty words (proves, clearly, always ...),
  a changed count of negations, repeated-number counts, a direction word that flips next to the same
  numbers (rose/fell, increased/decreased, higher/lower, improved/degraded), the two numbers of
  "from X to Y" swapped, and structural flattening: sentence-length CV (short sentences included)
  or paragraph-length variation dropping sharply, or the text growing or shrinking by more than a third.

LaTeX awareness: comments, preamble, floats and tables are skipped; \\cite{a,b} contributes the keys a
and b as facts; $math$ is compared as a unit (simple numeric math such as $0.02\\%$ is read as text);
formatting commands are unwrapped so wording can change around them.

Usage
  python verify_rewrite.py source.md rewrite.md
  python verify_rewrite.py old.tex new.tex --strict --json
  python verify_rewrite.py old.md new.md --lenient-hedges

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
from decimal import Decimal, InvalidOperation

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
# 3 x 10^-4, 3\times10^{-4}, 3 \cdot 10^{-4} -> 3e-4 ; a bare 10^{-4} -> 1e-4
SCI_RE = re.compile(r"(\d(?:[\d.,]*\d)?)\s*(?:[x\u00d7\u00b7*]|\\times|\\cdot)\s*10\s*\^\s*\{?\s*\(?\s*([-+\u2212]?)\s*(\d+)\s*\)?\s*\}?")
POW10_RE = re.compile(r"(?<![\w.^])10\s*\^\s*\{?\s*\(?\s*([-+\u2212]?)\s*(\d+)\s*\)?\s*\}?")


def sci_to_e(t):
    t = SCI_RE.sub(lambda m: "%se%s%s" % (m.group(1), m.group(2), m.group(3)), t)
    return POW10_RE.sub(lambda m: "1e%s%s" % (m.group(1), m.group(2)), t)


def math_to_plain(m):
    t = m
    # \sim becomes the approximately-equal sign: a bare "~" is a LaTeX tie and is dropped later
    for a, b in (("{,}", ","), ("\\%", "%"), ("\\,", ""), ("\\;", ""), ("\\!", ""), ("\\ ", ""),
                 ("{\\sim}", "\u2248"), ("\\sim", "\u2248"), ("\\geq", "\u2265"), ("\\ge", "\u2265"),
                 ("\\leq", "\u2264"), ("\\le", "\u2264"), ("\\pm", "\u00b1"), ("\\times", "\u00d7"),
                 ("\\cdot", "\u00b7"), ("\\approx", "\u2248"), ("{", ""), ("}", "")):
        t = t.replace(a, b)
    return sci_to_e(t)


def numeric_math(plain):
    """True if a math span is only a number (exponents allowed), so it is read as text."""
    return bool(NUMERIC_MATH_RE.match(re.sub(r"(?<=\d)e[-+\u2212]?\d+", "", plain)))


AY_NAME = r"[A-Z][A-Za-z\-']+(?:\s+et\s+al\b\.?|\s+(?:and|&)\s+[A-Z][A-Za-z\-']+)?"
AY_PAREN_RE = re.compile(r"\((?:(?:e\.g\.|see|cf\.)[,\s]+)?(" + AY_NAME + r",?\s+\d{4}[a-z]?(?:\s*;[^)]*)?)\)")
AY_NARR_RE = re.compile(r"\b(" + AY_NAME + r")\s+\((\d{4}[a-z]?)\)")


def ay_key(s):
    """One spelling for an author-year key: 'Smith et al., 2020' == 'Smith et al. 2020'."""
    s = re.sub(r"\s*&\s*", " and ", s).replace(",", " ")
    s = re.sub(r"\bet\s+al\b\.?", "et al.", s)
    return re.sub(r"\s+", " ", s).strip()


def author_year(s, facts):
    """Record author-year citations, parenthetical (Smith et al., 2020; Lee, 2019) or narrative
    Smith et al. (2020), as one key per work, so moving between the two forms is not a lost fact."""
    def paren_cb(m):
        for part in m.group(1).split(";"):
            if part.strip():
                facts.add("citation", ay_key(part), line_of(m))
        return CITE_P
    s = AY_PAREN_RE.sub(paren_cb, s)

    def narr_cb(m):
        facts.add("citation", ay_key(m.group(1) + " " + m.group(2)), line_of(m))
        return AUTH
    return AY_NARR_RE.sub(narr_cb, s)


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
    s = author_year(s, facts)

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
        if numeric_math(plain):
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

    s = author_year(s, facts)
    # LaTeX-style commands that sometimes appear in Markdown (pandoc, Overleaf notes)
    s = CITE_RE.sub(lambda m: (
        [facts.add("citation", k.strip(), line_of(m)) for k in m.group(3).split(",") if k.strip()],
        CITE_P)[1], s)

    def mm(m):
        inner = next(g for g in m.groups() if g is not None)
        plain = math_to_plain(inner)
        if numeric_math(plain):
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

NUM_SMALL = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
             "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
             "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
NUM_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80,
            "ninety": 90}
NUM_MULT = {"hundred": 100, "thousand": 1000, "million": 1000000, "billion": 1000000000}
NUMWORDS = dict(NUM_SMALL, **NUM_TENS, **NUM_MULT)
_NW = "(?:" + "|".join(sorted(NUMWORDS, key=len, reverse=True)) + ")"
# a run of number words: "two hundred", "twenty-five", "three thousand five hundred and six"
NUMWORD_RE = re.compile(r"\b" + _NW + r"(?:(?:[ \t]*-[ \t]*|[ \t]+(?:and[ \t]+)?)" + _NW + r")*\b", re.I)
DIGIT_MULT_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)[ \t]+(hundred|thousand|million|billion)\b", re.I)
# "one" is the pronoun, not a count, in "one of", "no one", "the one that", "on one hand" ...
ONE_PRONOUN_BEFORE = re.compile(r"\b(?:no|any|every|some|each|the|this|that|which|anyone|someone)\s+$", re.I)
ONE_PRONOUN_AFTER = re.compile(r"\s*(?:$|[^\w\s-]|(?:of|another|or|and|the|a|an|that|which|who|whom|whose|can|could|may|"
                               r"might|will|would|should|must|is|was|are|were|has|had|does|did|to|in|on|at|by|for|"
                               r"with|from|as|than|hand|side|way|such|another|else)\b)", re.I)
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
# group 1 the mantissa, group 2 the exponent (3e-4, 1.5E-3): the exponent is part of the value
NUM_RE = re.compile(r"(?<![\w.])(" + NUM_CORE + r")(?:[eE]([-+\u2212]?\d+))?")
EXP_TOK_RE = re.compile(r"E[-+\u2212]?\d+")
FROM_TO_RE = re.compile(r"\bfrom\s+(?:about\s+|~\s*)?(" + NUM_CORE + r")(?:[eE]([-+\u2212]?\d+))?(?:\s*%|\s+[A-Za-z]+)?"
                        r"\s+to\s+(?:about\s+|~\s*)?(" + NUM_CORE + r")(?:[eE]([-+\u2212]?\d+))?", re.I)
# a qualifier fixed to the number that follows it: approximators and bounds
QUAL_RE = re.compile(r"(?:\b(about|approximately|approx\.|roughly|around|nearly|almost|circa|ca\.)|(~|\u2248|\u223c)|"
                     r"\b(more than|greater than|at least|no less than|not less than|no fewer than|less than|fewer than|"
                     r"at most|up to|no more than|not more than)|(<=|>=|\u2264|\u2265|<|>))\s*$", re.I)
QUAL_CANON = {"more than": ">", "greater than": ">", "at least": ">=", "no less than": ">=", "not less than": ">=",
              "no fewer than": ">=", "less than": "<", "fewer than": "<", "at most": "<=", "up to": "<=",
              "no more than": "<=", "not more than": "<=", "<=": "<=", ">=": ">=", "\u2264": "<=",
              "\u2265": ">=", "<": "<", ">": ">"}
CAP_RE = re.compile(r"[A-Z][A-Za-z0-9]*(?:[-.](?=[A-Za-z0-9])[A-Za-z0-9]+)*(?:['\u2019]s)?")
STOP_CAPS = {"Figure", "Fig", "Table", "Section", "Sec", "Appendix", "Eq", "Equation", "Theorem", "Lemma",
             "Algorithm", "Chapter", "Proposition", "Definition", "Corollary", "Remark", "Example", "Step",
             "Part", "Panel", "I"}
# ordinary words: capitalised at the start of a sentence they are not proper nouns; lower-case they
# carry no claim on their own, so they are not used to anchor a negation or hedge either
COMMON_WORDS = set("""
a about above across after afterwards again against all almost along also although always among an and another
any anything are around as at because been before being below between beyond both but by can could did do does
doing done down due during each either else even ever every first for from further furthermore given had has
have having he hence her here hers his how however if in indeed instead into is it its itself just last later
least less like likewise many may meanwhile might more moreover most much must namely near nevertheless next
nonetheless now of off often on once one only onto or other otherwise our ours out over overall per perhaps
rather same second several she should similarly since so some such than that the their theirs them then there
thereby therefore these they third this those though through throughout thus to together too toward towards
under unless unlike until up upon us very via was we well were what whatever when whenever where whereas
wherever whether which while who whom whose why will with within without would yet you your finally
specifically notably importantly crucially accordingly consequently still besides let note we're it's let's
using based compared following
""".split())
ABBR_BEFORE_PERIOD = {"e.g", "i.e", "vs", "cf", "al", "fig", "eq", "sec", "no", "approx", "resp", "etc", "dr",
                      "mr", "ms", "prof", "st"}


def norm_number(txt, exp=None):
    """Canonical text of a number. Thousands separators go; trailing zeros stay (0.50 is not 0.5).
    A number with an exponent, or one below 0.001, is written as mantissa e exponent with the
    mantissa's digits kept: 3e-4 == 3E-4 == 3 x 10^-4 == 0.0003, and 3.0e-4 keeps its precision."""
    t = txt.replace(",", "")
    if t.startswith("."):
        t = "0" + t
    if exp is None and not re.match(r"0\.000\d", t):
        return t
    try:
        d = Decimal(t + ("e" + exp.replace("\u2212", "-") if exp else ""))
    except InvalidOperation:
        return t
    sign, digits, e = d.as_tuple()
    digits = list(digits)
    while len(digits) > 1 and digits[0] == 0:
        digits.pop(0)
    mant = str(digits[0]) + ("." + "".join(str(x) for x in digits[1:]) if len(digits) > 1 else "")
    return "%s%se%d" % ("-" if sign else "", mant, e + len(digits) - 1)


def numwords_to_digits(m):
    """NUMWORD_RE callback: 'two hundred' -> '200', 'twenty-five' -> '25', 'two and three' -> '2 and 3'."""
    words = re.findall(r"[A-Za-z]+", m.group(0))
    if len(words) == 1 and words[0].lower() == "one":
        if ONE_PRONOUN_BEFORE.search(m.string[max(0, m.start() - 12):m.start()]) or \
                ONE_PRONOUN_AFTER.match(m.string[m.end():m.end() + 12]):
            return m.group(0)
    out = []
    tot, cur, last, pend = 0, 0, None, False

    def close():
        if last is not None:
            out.append(str(tot + cur))
        if pend:
            out.append("and")
    for w in words:
        lw = w.lower()
        if lw == "and":
            if last in ("hund", "big") and not pend:
                pend = True   # "two hundred and five"; kept only if a number word follows
            else:
                close()
                out.append("and")
                tot, cur, last, pend = 0, 0, None, False
            continue
        if lw in NUM_SMALL or lw in NUM_TENS:
            v = NUMWORDS[lw]
            if not (last is None or last in ("hund", "big") or (last == "tens" and 1 <= v <= 9)):
                close()
                tot, cur, last = 0, 0, None
            cur += v
            last = "tens" if lw in NUM_TENS else "small"
        elif lw == "hundred":
            if last in ("small", "tens") and 0 < cur < 100:
                cur *= 100
            elif last is None:
                cur = 100
            else:
                close()
                tot, cur = 0, 100
            last = "hund"
        else:
            v = NUM_MULT[lw]
            if last in ("small", "tens", "hund"):
                tot, cur = tot + max(cur, 1) * v, 0
            else:
                close()
                tot, cur = v, 0
            last = "big"
        pend = False
    close()
    return " ".join(out)


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
        if is_exponent(m):
            continue
        start = sentence_start(t, m.start())
        has_digit = any(c.isdigit() for c in tok)
        camel = has_digit or sum(1 for c in tok if c.isupper()) >= 2
        nxt = re.match(r" ([A-Z][A-Za-z0-9]*)", t[m.end():m.end() + 40])
        nextcap = bool(nxt and re.match(r"[A-Z][a-z]", nxt.group(1)) and nxt.group(1) not in STOP_CAPS
                       and nxt.group(1) not in PLACEHOLDERS)
        caps_out.append({"tok": tok, "line": line_of(m), "start": start, "camel": camel, "nextcap": nextcap,
                         "digit": has_digit})
    # remove identifier tokens containing digits so their digits are not read as numbers
    t2 = CAP_RE.sub(lambda m: " " if any(c.isdigit() for c in m.group(0)) and not is_exponent(m) else m.group(0), t)
    t2 = re.sub(r"(?<!\w)\(\d{1,2}\)(?=\s)", " ", t2)
    t2 = re.sub(r"(?m)^\s*\d{1,2}[.)]\s", " ", t2)
    t2 = re.sub(r"\[@c\]|URL|MATH|REF", " ", t2)
    # spelled numbers become digits ("1.5 million" and "two million" too); 3 x 10^-4 becomes 3e-4
    t2 = DIGIT_MULT_RE.sub(lambda m: format((Decimal(m.group(1).replace(",", "")) * NUM_MULT[m.group(2).lower()]).normalize(), "f"), t2)
    t2 = NUMWORD_RE.sub(numwords_to_digits, t2)
    t2 = sci_to_e(t2)
    # "from X to Y": the order is part of the claim
    for m in FROM_TO_RE.finditer(t2):
        facts.add("order", "%s -> %s" % (norm_number(m.group(1), m.group(2)), norm_number(m.group(3), m.group(4))),
                  line_of(m))
    # ranges with units: "78-107%" -> "78 % 107 %"
    t2 = RANGE_RE.sub(lambda m: "%s %s %s %s" % (m.group(1), m.group(3), m.group(2), m.group(3)), t2)
    for m in NUM_RE.finditer(t2):
        raw = m.group(1)
        val = norm_number(raw, m.group(2))
        pre = t2[max(0, m.start() - 2):m.start()]
        sign = ""
        if pre.endswith(("-", "\u2212")) and (len(pre) < 2 or pre[0] in " (\n"):
            sign = "-"
        unit = unit_after(t2, m.end())
        full = sign + val
        if unit:
            value, kind = "%s %s" % (full, unit), "number"
        elif re.fullmatch(r"(?:19|20)\d\d", val):
            value, kind = val, "year"
        else:
            value, kind = full, "number"
        facts.add(kind, value, line_of(m))
        q = QUAL_RE.search(t2[max(0, m.start() - 24):m.start() - len(sign)])
        if q:
            word = (q.group(1) or q.group(3) or q.group(4) or "").lower()
            facts.add("qualifier", "%s %s" % (QUAL_CANON.get(word, "~"), value), line_of(m))
    return t


def is_exponent(m):
    """A CAP_RE match that is the exponent of a number written like 1.5E-3."""
    return bool(EXP_TOK_RE.fullmatch(m.group(0)) and m.start() > 0 and m.string[m.start() - 1].isdigit())


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
# "not only ... but also" and bounds such as "no more than 5%" are not negated claims (the bound is
# compared as a qualifier of its number instead)
NEG_RE = re.compile(r"\b(?:not(?!\s+(?:only|just|merely)\b)(?!\s+(?:more|less|fewer)\s+than\b)|"
                    r"no(?!\s+(?:more|less|fewer|longer)\s+than\b)(?!\.\s*\d)|never|neither|nor|cannot|without|none|"
                    r"nothing|nobody|nowhere|lacks?|lacked|lacking|absent|absence|unable|insignificant|"
                    r"non-?significant|fail(?:s|ed)?\s+to)\b|n't|n\u2019t", re.I)
# negation tied to a claim: as NEG_RE, but "without" is left out ("removing X" -> "without X" is a
# paraphrase), and contrastive "rather than" / "instead of" count ("A, rather than B" == "A, not B")
CLAIM_NEG_RE = re.compile(r"\b(?:not(?!\s+(?:only|just|merely)\b)(?!\s+(?:more|less|fewer)\s+than\b)|"
                          r"no(?!\s+(?:more|less|fewer|longer)\s+than\b)(?!\.\s*\d)|never|neither|nor|cannot|none|"
                          r"nothing|nobody|nowhere|lacks?|lacked|lacking|absent|absence|unable|insignificant|"
                          r"non-?significant|fail(?:s|ed)?\s+to|rather\s+than|instead\s+of)\b|n't|n\u2019t", re.I)
# hedges that change what a claim asserts; removing one strengthens the claim. "could" only counts in
# its hedging sense ("could reflect"), not as ability ("we could train"); approximators directly before
# a number are compared per number (see QUAL_RE) and are skipped here.
MEANING_HEDGE_RE = re.compile(
    r"\b(?:may(?!\s+\d)|might|could(?=\s+(?:be|have|reflect|explain|indicate|arise|account|result|stem|"
    r"contribute|lead|affect|influence|drive|cause|also|partly|potentially)\b)|suggest(?:s|ed|ing)?|"
    r"seem(?:s|ed|ingly)?|appear(?:s|ed)?\s+to|tend(?:s|ed)?\s+to|possibly|perhaps|potentially|probably|"
    r"(?:un)?likely|presumably|arguably|plausibly|conceivably|roughly|approximately|nearly|almost|"
    r"tentative(?:ly)?|speculat\w*|hypothesi[sz]\w*|preliminary)\b", re.I)
APPROX_BEFORE_NUM_RE = re.compile(r"\s*[~\u2248]?\s*[-\u2212]?(?:\d|\.\d)")
DIRECTION = {
    "up": re.compile(r"\b(?:rose|rise[sn]?|rising|increas\w*|higher|grew|grow(?:s|n|ing)?|improv\w*|gained|greater|"
                     r"larger|exceed\w*|boost\w*|outperform\w*)\b", re.I),
    "down": re.compile(r"\b(?:fell|fall(?:s|en|ing)?|drop(?:s|ped|ping)?|decreas\w*|declin\w*|lower(?:ed|s)?|"
                       r"reduc\w*|shrank|shrunk|shrink\w*|degrad\w*|worse\w*|smaller|underperform\w*)\b", re.I),
}
# clause boundaries inside a sentence: a negation or hedge is tied to the claim in its own clause
CLAUSE_SPLIT_RE = re.compile(r"\s*;\s*|(?<!\d)\s*:\s*(?!\d)|\s*\u2014\s*|,?\s+(?=(?:but|while|whereas|although|though|unlike)\b)|,\s+(?=yet\b)", re.I)


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
            # short sentences ("It failed.", "Why?") are the rhythm: they must count, or a source
            # whose punch lives in them looks as flat as its flattened rewrite
            n = nwords(s)
            if n >= 1:
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
    """A capitalised word is a proper noun mid-sentence. At the start of a sentence it is one only if it
    is multi-capital or has a digit, appears capitalised mid-sentence somewhere, or is followed by
    another capitalised name and is neither an ordinary word nor used in lower case in either text
    ("Smith Labs", but not "As Table" or "In Figure")."""
    mid = set()
    lower = set()
    for d in docs:
        lower.update(w for w in re.findall(r"\b[a-z][a-z'\-]*\b", d.text))
        for c in d.caps:
            if not c["start"]:
                mid.add(c["tok"])
    for d in docs:
        for c in d.caps:
            tok = c["tok"]
            low = tok.lower()
            ordinary = low in COMMON_WORDS or low in lower
            ok = (not c["start"]) or c["camel"] or tok in mid or (c["nextcap"] and not ordinary)
            if ok:
                d.facts.add("proper noun", tok, c["line"])


def proper_noun_set(docs):
    out = set()
    for d in docs:
        out.update(d.facts.kinds("proper noun"))
    return out


def claim_units(doc, pn):
    """Cut the text into clauses. Each clause carries its anchors (facts weigh 3: numbers, years, proper
    nouns; content-word stems weigh 1), its negations, meaning-bearing hedges and direction words."""
    text = doc.text
    prot = text
    for a in ABBR:
        prot = prot.replace(a, a.replace(".", "\x02"))
    units = []

    def para(off, end):
        pos = off
        bounds = [m.start() + off for m in SPLIT_RE.finditer(prot[off:end])] + [end]
        for b in bounds:
            sent = text[pos:b]
            if sent.strip():
                lead = len(sent) - len(sent.lstrip())
                line = text.count("\n", 0, pos + lead) + 1
                shown = re.sub(r"\s+", " ", sent).strip()
                if len(shown) > 220:
                    shown = shown[:217] + "..."
                for cl in CLAUSE_SPLIT_RE.split(sent):
                    if cl and cl.strip():
                        units.append(clause_info(cl, pn, shown, line))
            pos = b
    pos = 0
    for sep in re.finditer(r"\n\s*\n|" + BREAK, prot):
        para(pos, sep.start())
        pos = sep.end()
    para(pos, len(prot))
    return units


def clause_info(cl, pn, sentence, line):
    tmp = Facts()
    extract_text_facts(cl, tmp, [])
    anchors = {}
    for kind in ("number", "year"):
        for v in tmp.kinds(kind):
            anchors[("n", v)] = 3
    for m in CAP_RE.finditer(cl):
        tok = m.group(0)[:-2] if m.group(0).endswith(("'s", "\u2019s")) else m.group(0)
        if tok in pn:
            anchors[("p", tok)] = 3
    for w in re.findall(r"[A-Za-z]+", cl):
        low = w.lower()
        if len(low) < 4 or low in COMMON_WORDS or w in PLACEHOLDERS or w in pn or NEG_RE.fullmatch(low) \
                or MEANING_HEDGE_RE.fullmatch(low):
            continue
        anchors.setdefault(("w", low[:5]), 1)
    hedges = [m.group(0).lower() for m in MEANING_HEDGE_RE.finditer(cl)
              if not (m.group(0).lower() in ("roughly", "approximately", "nearly", "almost")
                      and APPROX_BEFORE_NUM_RE.match(cl, m.end()))]
    return {"sentence": sentence, "line": line, "anchors": anchors,
            "negation": [re.sub(r"\s+", " ", m.group(0).lower()) for m in CLAIM_NEG_RE.finditer(cl)], "hedge": hedges,
            "dirs": {k for k, rx in DIRECTION.items() if rx.search(cl)}}


def claim_matches(u, others):
    """The clauses of the other text that carry this clause's claim: those whose shared anchor weight
    is at least half of the best match. None when nothing matches well enough to judge."""
    scored = [(sum(w for a, w in u["anchors"].items() if a in o["anchors"]), o) for o in others]
    best = max((s for s, _ in scored), default=0)
    if best < 2:
        return None
    return [o for s, o in scored if s and s >= 0.5 * best]


def unmatched_marker(u, mine, theirs, kind):
    """True if clause u (in `mine`) carries a `kind` marker that no counterpart in `theirs` carries.
    A counterpart is a clause u matches well, or a marked clause that matches u well (so a hedge that
    moved into a clause split off from u still counts). None of them matching at all: no verdict."""
    ms = claim_matches(u, theirs)
    if ms is None:
        return False
    if any(o[kind] for o in ms):
        return False
    for o in theirs:
        if o[kind]:
            back = claim_matches(o, mine)
            if back and any(x is u for x in back):
                return False
    return True


def compare_claims(src, new):
    """Negations and hedges tied to claims, direction words next to the same numbers.
    Returns (lost, gained, direction warnings, source units, rewrite units); lost and gained are
    lists of (kind, unit)."""
    pn = proper_noun_set([src, new])
    su, nu = claim_units(src, pn), claim_units(new, pn)
    lost, gained, dirw = [], [], []
    for kind in ("negation", "hedge"):
        for mine, theirs, out in ((su, nu, lost), (nu, su, gained)):
            seen = set()
            for u in mine:
                if u[kind] and u["sentence"] not in seen and unmatched_marker(u, mine, theirs, kind):
                    seen.add(u["sentence"])
                    out.append((kind, u))
    for u in su:
        nums = {a for a in u["anchors"] if a[0] == "n"}
        if not u["dirs"] or not nums:
            continue
        ms = [o for o in (claim_matches(u, nu) or []) if nums & set(o["anchors"])]
        nd = set().union(*[o["dirs"] for o in ms]) if ms else set()
        if nd and not (u["dirs"] & nd):
            dirw.append("direction word flipped next to %s: source says %s (line %d: %s), rewrite says %s; check "
                        "the claim did not reverse" % (", ".join(sorted(a[1] for a in nums)), "/".join(sorted(u["dirs"])),
                                                       u["line"], u["sentence"], "/".join(sorted(nd))))
    return lost, gained, dirw, su, nu


KIND_ORDER = ["number", "year", "proper noun", "citation", "url", "quote", "ref", "label", "math", "macro"]


def first_sentence(units, value):
    for u in units:
        if ("n", value) in u["anchors"]:
            return u["sentence"]
    return ""


def compare(src, new, strict, lenient_hedges=False, lenient_negations=False):
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
    # claim markers: negations and meaning-bearing hedges tied to their clause's facts
    lost, gained, dirw, su, nu = compare_claims(src, new)
    lenient = {"negation": lenient_negations, "hedge": lenient_hedges}
    for side, items, out in (("source", lost, dropped), ("rewrite", gained, added)):
        for kind, u in items:
            words = ", ".join(sorted(set(u[kind])))
            if lenient[kind]:
                warns.append({"type": kind, "msg": "%s %s: '%s' (%s line %d) has no counterpart in the matching "
                              "%s sentence(s): %s" % (kind, "lost" if side == "source" else "added", words, side,
                                                     u["line"], "rewrite" if side == "source" else "source",
                                                     u["sentence"]), "strict_fail": True})
            else:
                out.append({"kind": kind, "value": words, "line": u["line"], "sentence": u["sentence"]})
    # qualifiers fixed to a number: about/~ (a hedge) and bounds (more than, at least, <, ...)
    nums_s = set(src.facts.kinds("number")) | set(src.facts.kinds("year"))
    nums_n = set(new.facts.kinds("number")) | set(new.facts.kinds("year"))
    qs, qn = src.facts.kinds("qualifier"), new.facts.kinds("qualifier")
    for doc, a, b, other_nums, units, out, side in ((src, qs, qn, nums_n, su, dropped, "lost"),
                                                    (new, qn, qs, nums_s, nu, added, "added")):
        for v in sorted(set(a) - set(b)):
            num = v.split(" ", 1)[1]
            if num not in other_nums:
                continue   # the number itself is DROPPED/ADDED already
            kind = "hedge" if v.startswith("~") else "qualifier"
            line = doc.facts.items[("qualifier", v)][1]
            if kind == "hedge" and lenient_hedges:
                warns.append({"type": "hedge", "msg": "approximator %s before %r (line %d): %s" %
                              (side, num, line, first_sentence(units, num)), "strict_fail": True})
            else:
                out.append({"kind": kind, "value": v, "line": line, "sentence": first_sentence(units, num)})
    # "from X to Y" reversed, direction words flipped next to the same numbers
    so, no = src.facts.kinds("order"), new.facts.kinds("order")
    for v in sorted(set(so) - set(no)):
        x, y = v.split(" -> ")
        rev = "%s -> %s" % (y, x)
        if rev in no and rev not in so:
            warns.append({"type": "order", "msg": "numbers swapped: source says 'from %s to %s' (line %d), rewrite says "
                          "'from %s to %s'" % (x, y, src.facts.items[("order", v)][1], y, x), "strict_fail": True})
    for msg in dirw:
        warns.append({"type": "direction", "msg": msg, "strict_fail": True})
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
                    "FAIL. A negation or meaning-bearing hedge lost from (or added to) a claim, matched by the "
                    "facts and words around it, also FAILs, as does an approximator or bound fixed to a number "
                    "('about 12%' -> '12%'). Overall hedge counts, negation counts, direction words, swapped "
                    "'from X to Y' numbers and rhythm produce warnings (failures with --strict).",
        epilog="Exit codes: 0 PASS, 1 FAIL, 2 unreadable input.")
    ap.add_argument("source", help="the original text (.tex, .md, .txt)")
    ap.add_argument("rewrite", help="the rewritten text")
    ap.add_argument("--strict", action="store_true",
                    help="also fail on vanished hedge families, changed negation count, changed repeat counts "
                         "of numbers/citations, flipped direction words, swapped 'from X to Y' numbers, "
                         "lenient hedge/negation warnings, and structural flattening")
    ap.add_argument("--lenient-hedges", action="store_true",
                    help="report a hedge or approximator lost from or added to a claim as a warning instead of a "
                         "failure (still a failure with --strict)")
    ap.add_argument("--lenient-negations", action="store_true",
                    help="report a negation lost from or added to a claim as a warning instead of a failure "
                         "(still a failure with --strict)")
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
    dropped, added, warns, sflag = compare(src, new, args.strict, args.lenient_hedges, args.lenient_negations)
    strict_fail = args.strict and (any(w["strict_fail"] for w in warns) or bool(sflag))
    failed = bool(dropped or added or strict_fail)
    n_warn = len(warns) + len(sflag)
    result = "FAIL" if failed else "PASS"

    if args.json:
        print(json.dumps({
            "result": result, "strict": args.strict, "lenient_hedges": args.lenient_hedges,
            "lenient_negations": args.lenient_negations, "source": args.source, "rewrite": args.rewrite,
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
        if d.get("sentence"):
            print("        in: %s" % d["sentence"])
    for a in added:
        print("ADDED   %-11s %r  (rewrite line %d)" % (a["kind"], a["value"], a["line"]))
        if a.get("sentence"):
            print("        in: %s" % a["sentence"])
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
