#!/usr/bin/env python3
"""check_numbers.py: find literal numbers in a LaTeX paper that should come from a numbers file.

Why: a number typed by hand goes stale the moment a result file regenerates. A paper
whose prose pulls every figure from a generated macro (\\newcommand{\\accA}{0.81}) cannot drift.

What it does
  1. Scans prose, captions and inline math of the .tex file (and files it \\input's, resolved
     like LaTeX: relative to the main file's directory first, then to the including file) for
     literal numbers, including e-notation (1e-3, 2.5e-4) and 3 \\times 10^{-4}. It ignores
     labels, refs, cite keys, URLs, dimensions, model-size tokens, layer-style names (L31, H28),
     "Figure 3" / "Eqs. (3)--(5)" / "row 17" style references, display equations and the preamble.
     An integer from 1900 to 2100 is skipped as a year only in year-like context ("in 2023",
     "since 2019", "(Smith et al., 2020)", "May 2021"); "2048 tokens" is checked like any number.
  2. With --numbers, reads macro definitions from the numbers file, counts how many of them the
     paper actually uses, and suggests a macro for any literal whose value matches one.
  3. With --results-dir, checks whether each specific literal (2+ decimals, one decimal and >= 10,
     any decimal in a table or percent, e-notation, or >= 100) appears, after rounding to the
     displayed precision, in any .txt, .csv, .json or .md result file under 2 MB. Not finding a number is a prompt to look, not proof of error:
     derived values (ratios, percentages) often live in no single file.

Usage
  python check_numbers.py paper/main.tex [--numbers paper/numbers.tex] [--results-dir results]
                          [--json] [--all] [--include-small] [--include-display]

Exit code is 0 unless the tex file cannot be read (then 2). Warnings (missing numbers file,
results dir or \\input'ed file) go to stderr, so --json output on stdout is always valid JSON;
they are also listed in the report (summary "warnings" in JSON).
"""
import argparse
import bisect
import json
import os
import re
import sys
import time

RESULT_EXTS = {".txt", ".csv", ".json", ".md"}
MAX_RESULT_FILE = 2 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env"}

NUM_RE = re.compile(
    r"(?P<sci>\d+(?:\.\d+)?\s*(?:\\times|\\cdot)\s*10\^\{?[-+]?\d+\}?|10\^\{?[-+]?\d+\}?"
    r"|\d+(?:\.\d+)?[eE][-+]?\d+(?![\dA-Za-z]))"
    r"|(?P<num>\d{1,3}(?:(?:\{,\}|,)\d{3})+(?!\d)(?:\.\d+)?|\d+(?:\.\d+)?)"
)

MASK_PATTERNS = [
    re.compile(r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\\[A-Za-z@]+\s*\}?\s*(?:\[\d\]\s*)?"
               r"(?:\[[^\]]*\]\s*)?\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}"),
    re.compile(r"\\[gex]?def\s*\\[A-Za-z@]+\s*(?:#\d\s*)*\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}"),
    re.compile(r"\\(?:url|nolinkurl|path|href)\s*\{[^{}]*\}"),
    re.compile(r"(?:https?|ftp)://[^\s{}]+|\bwww\.[^\s{}]+"),
    re.compile(r"\\(?:label|ref|eqref|autoref|cref|Cref|pageref|nameref|vref|cite[a-zA-Z]*|parencite|textcite|"
               r"input|include|includegraphics|usepackage|RequirePackage|documentclass|bibliography|"
               r"bibliographystyle|graphicspath|url|hypersetup|setlength|addtolength|vspace|hspace|"
               r"newcommand|renewcommand|providecommand|newenvironment|geometry|includepdf|"
               r"addbibresource|tag|setcounter|addtocounter|newtheorem|newcounter|hyperref|"
               r"fontsize|linespread|setstretch)\*?\s*(?:\[[^\]]*\]\s*)*(?:\{[^{}]*\})?"),
    re.compile(r"\\begin\{(?:tabular|tabularx|array|minipage|longtable|wrapfigure|tabulary)\*?\}\s*"
               r"(?:\[[^\]]*\]\s*)?(?:\{[^{}]*\})?"),
    re.compile(r"\\(?:begin|end)\{[^{}]*\}(?:\[[^\]]*\])?"),
    re.compile(r"\\\\\s*\[[^\]]*\]"),
    re.compile(r"\d*\.?\d+\s*(?:pt|cm|mm|in|em|ex|bp|sp|pc)(?![A-Za-z])"),
    re.compile(r"\d*\.?\d+\s*\\(?:linewidth|textwidth|columnwidth|textheight|paperwidth|hsize|baselineskip)"),
    re.compile(r"\\(?:section|subsection|subsubsection|paragraph)\*?\s*\{[^{}]*\}"),
]
REF_WORDS = (r"(?:(?<![A-Za-z])(?i:Figures?|Figs?\.?|Tables?|Tabs?\.?|Sections?|Secs?\.?|Eqs?\.?|Equations?|"
             r"Appendix|Appendices|Algorithms?|Algs?\.?|Theorems?|Lemmas?|Propositions?|Corollar(?:y|ies)|"
             r"Definitions?|Remarks?|Assumptions?|Examples?|Pages?|pp?\.|Lines?|Rows?|Columns?|Cols?\.|Steps?|"
             r"Panels?|Box|Chapters?|Ch\.?|Footnotes?|Listings?)|\\S|\\P)")
REF_PREFIX = re.compile(REF_WORDS + r"[\s~\\]*(?:\\,)?\(?$")
# "Eqs.~(3)--(" / "Figs.~2 and " / "Tables 2, 3 and ": a later member of a reference list or range
REF_ITEM = r"\(?\d+(?:\.\d+)*[a-z]?\)?"
REF_SEP = r"\s*(?:--|-|\u2013|,\s*and|,|and|&|to|or)\s*"
REF_CHAIN = re.compile(REF_WORDS + r"[\s~\\]*(?:\\,)?" + REF_ITEM + r"(?:" + REF_SEP + REF_ITEM + r")*" + REF_SEP
                       + r"[~\\]*\(?$")
MONTHS = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
          r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?")
YEAR_BEFORE = re.compile(r"(?:(?<![A-Za-z])(?i:in|since|until|till|from|during|by|before|after|circa|early|late|"
                         r"spring|summer|autumn|fall|winter|year|between)|" + MONTHS + r"|et\s+al\.?,?|"
                         r"[A-Z][A-Za-z\-]+,|\(|\d{4}\s*(?:--|-|\u2013|and|to)\s*)[\s~]*$")
YEAR_AFTER = re.compile(r"[\s~]*(?:" + MONTHS + r"(?![A-Za-z])|[a-z]?\s*[);]|(?:--|-|\u2013)\s*\d{4}(?!\d))")
COUNT_NOUN = re.compile(r"\s+(?:[a-z\-]+\s+)?(?:tokens?|examples?|samples?|steps?|epochs?|images?|parameters?|"
                        r"params|words?|documents?|sentences?|iterations?|queries|query|pairs?|instances?|"
                        r"points?|items?|questions?|tasks?|episodes?|frames?|pixels?|units?|neurons?|"
                        r"dimensions?|dims?|features?|nodes?|edges?|users?|rows?|files?|runs?|trials?|"
                        r"participants?|subjects?|patients?|records?|entries|batches|clips?|hours?|GPUs?)\b")


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def blank(s):
    return re.sub(r"[^\n]", " ", s)


def strip_comments(text):
    out = []
    for line in text.split("\n"):
        i, n = 0, len(line)
        cut = None
        while i < n:
            c = line[i]
            if c == "\\":
                i += 2
                continue
            if c == "%":
                cut = i
                break
            i += 1
        out.append(line if cut is None else line[:cut] + " " * (n - cut))
    return "\n".join(out)


def mask_spans(text):
    chars = list(text)
    start = text.find("\\begin{document}")
    if start > 0:
        for i in range(start):
            if chars[i] != "\n":
                chars[i] = " "
    t = "".join(chars)
    for pat in MASK_PATTERNS:
        t = pat.sub(lambda m: blank(m.group(0)), t)
    return t


def brace_span(text, open_idx):
    depth = 0
    i = open_idx
    while i < len(text):
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text) - 1


def caption_spans(text):
    spans = []
    for m in re.finditer(r"\\caption(?:\[[^\]]*\])?\s*\{", text):
        o = m.end() - 1
        spans.append((o, brace_span(text, o)))
    return spans


def env_events(text):
    ev = []
    for m in re.finditer(r"\\(begin|end)\{([^{}]*)\}", text):
        ev.append((m.start(), m.group(1), m.group(2)))
    return ev


MATH_ENVS = {"equation", "equation*", "align", "align*", "eqnarray", "eqnarray*", "gather", "gather*",
             "multline", "multline*", "displaymath", "split", "flalign", "flalign*"}
TABLE_ENVS = {"tabular", "tabularx", "array", "longtable", "tabulary", "tabular*"}


def classify_regions(text):
    """Return sorted interval lists: display math, inline math."""
    disp, inl = [], []
    stack = []
    for pos, kind, name in env_events(text):
        if name in MATH_ENVS:
            if kind == "begin":
                stack.append((name, pos))
            elif stack:
                for k in range(len(stack) - 1, -1, -1):
                    if stack[k][0] == name:
                        disp.append((stack[k][1], pos))
                        del stack[k:]
                        break
    for m in re.finditer(r"(?<!\\)\\\[.*?\\\]", text, re.S):
        disp.append((m.start(), m.end()))
    for m in re.finditer(r"(?<!\\)\$\$.*?(?<!\\)\$\$", text, re.S):
        disp.append((m.start(), m.end()))
    t2 = text
    for a, b in disp:
        t2 = t2[:a] + blank(t2[a:b]) + t2[b:]
    inside, start = False, 0
    i = 0
    while i < len(t2):
        c = t2[i]
        if c == "\\":
            i += 2
            continue
        if c == "$":
            if not inside:
                inside, start = True, i
            else:
                inl.append((start, i))
                inside = False
        i += 1
    for m in re.finditer(r"(?<!\\)\\\(.*?\\\)", t2, re.S):
        inl.append((m.start(), m.end()))
    for m in re.finditer(r"\\begin\{math\}.*?\\end\{math\}", t2, re.S):
        inl.append((m.start(), m.end()))
    return merge_intervals(disp), merge_intervals(inl)


def merge_intervals(intervals):
    """Sort and merge overlapping or nested intervals so a bisect lookup sees the covering one."""
    out = []
    for a, b in sorted(intervals):
        if out and a <= out[-1][1]:
            if b > out[-1][1]:
                out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def in_any(intervals, pos):
    starts = [a for a, _ in intervals]
    k = bisect.bisect_right(starts, pos) - 1
    return k >= 0 and intervals[k][0] <= pos <= intervals[k][1]


def table_intervals(text):
    out, stack = [], []
    for pos, kind, name in env_events(text):
        if name in TABLE_ENVS:
            if kind == "begin":
                stack.append((name, pos))
            elif stack:
                a = stack.pop()
                out.append((a[1], pos))
    return merge_intervals(out)


SCI_PARTS = re.compile(r"(?:(\d+(?:\.\d+)?)\s*(?:\\times|\\cdot)\s*)?10\^\{?([-+]?\d+)\}?$|(\d+(?:\.\d+)?)[eE]([-+]?\d+)$")


def num_value(token):
    t = token.replace("{,}", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        pass
    m = SCI_PARTS.match(t.strip())
    if m:
        mant, exp = (m.group(1) or "1", m.group(2)) if m.group(2) is not None else (m.group(3), m.group(4))
        try:
            return float(mant) * 10.0 ** int(exp)
        except (ValueError, OverflowError):
            return None
    return None


def decimals_of(token):
    """Decimal places shown; for 2.5e-4 or 3 \\times 10^{-4} the place of the last shown digit (may be < 0)."""
    t = token.replace("{,}", "").replace(",", "")
    m = SCI_PARTS.match(t.strip())
    if m:
        mant, exp = (m.group(1) or "1", m.group(2)) if m.group(2) is not None else (m.group(3), m.group(4))
        return (len(mant.split(".")[1]) if "." in mant else 0) - int(exp)
    return len(t.split(".")[1]) if "." in t else 0


PERCENT_AFTER = re.compile(r"(?:\s|~|\\[,;: ]|\\thinspace\s*)*(?:\\%|%|\\percent(?![A-Za-z])|percent\b)"
                           r"|\}\s*\{\s*\\percent\s*\}")
SIGN_BEFORE = re.compile(r"(?:\\text\{--?\}|\\textminus|\\minus|\$-\$)\s*$|(?:\u2212|\{-\}|(?<![A-Za-z0-9\-])-)$")


def candidate_numbers(masked):
    """NUM_RE matches as (start, end, token, is_sci); a tuple like (64,128) is split into its members."""
    out = []
    for m in NUM_RE.finditer(masked):
        s, e, tok = m.start(), m.end(), m.group(0)
        if m.group("num") and "," in tok and "{,}" not in tok:
            lead = tok.split(",", 1)[0]
            prev = masked[s - 1] if s > 0 else " "
            nxt = masked[e] if e < len(masked) else " "
            tuple_like = (prev in "([," and nxt in ")],") and (len(lead) > 1 or prev == ",")
            if tuple_like:
                pos = s
                for part in tok.split(","):
                    out.append((pos, pos + len(part), part, False))
                    pos += len(part) + 1
                continue
        out.append((s, e, tok, bool(m.group("sci"))))
    return out


def find_literals(text, include_small, include_display):
    clean = strip_comments(text)
    masked = mask_spans(clean)
    caps = caption_spans(clean)
    disp, inl = classify_regions(clean)
    tabs = table_intervals(clean)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    lits = []
    for s, e, tok, is_sci in candidate_numbers(masked):
        kind = "scientific" if is_sci else "number"
        before = masked[max(0, s - 60):s]
        after = masked[e:e + 3]
        prev = masked[s - 1] if s > 0 else " "
        if prev.isalpha() or prev in "_\\" or (prev == "-" and s > 1 and masked[s - 2].isalpha()):
            continue
        if REF_PREFIX.search(before) or REF_CHAIN.search(before):
            continue
        if kind == "number":
            if after[:1].isalpha() and after[:1] not in "kx":
                continue
            if after[:1] == "_":
                continue
            if PERCENT_AFTER.match(masked, e):
                kind = "percent"
            val = num_value(tok)
            if val is None:
                continue
            if kind == "number" and "." not in tok and "," not in tok and "{" not in tok:
                if 1900 <= val <= 2100 and is_year_context(masked, s, e):
                    continue
                if val < 10 and not include_small:
                    continue
            if kind == "percent" and "." not in tok and val < 1 and not include_small:
                continue
        if not include_display and in_any(disp, s):
            continue
        where = "prose"
        if any(a <= s <= b for a, b in caps):
            where = "caption"
        elif in_any(tabs, s):
            where = "table"
        elif in_any(inl, s):
            where = "inline-math"
        sign = ""
        pre = masked[max(0, s - 12):s]
        if SIGN_BEFORE.search(pre):
            sign = "-"
        elif pre.endswith("{+}") or pre.endswith("+"):
            sign = "+"
        ln = bisect.bisect_right(line_starts, s)
        ctx = re.sub(r"\s+", " ", clean[max(0, s - 40):e + 40]).strip()
        val = num_value(tok)
        if val is not None and sign == "-":
            val = -val
        lits.append({"line": ln, "token": sign + tok + ("%" if kind == "percent" else ""),
                     "value": val, "decimals": decimals_of(tok),
                     "kind": kind, "where": where, "context": ctx})
    return lits, clean


def is_year_context(masked, s, e):
    """An integer 1900-2100 counts as a year only next to year-like words, months or a citation."""
    after = masked[e:e + 40]
    if COUNT_NOUN.match(after):
        return False
    return bool(YEAR_BEFORE.search(masked[max(0, s - 30):s]) or YEAR_AFTER.match(after))


def resolve_input(name, dirs):
    """Find an \\input'ed file the way LaTeX does: each directory in order, name as given, then name.tex."""
    for d in dirs:
        base = os.path.join(d, name)
        for cand in ((base, base + ".tex") if os.path.splitext(name)[1] else (base + ".tex", base)):
            if os.path.isfile(cand):
                return cand
    return None


def read_with_inputs(path, seen=None, depth=0, main_dir=None, warnings=None):
    """Return [(path, text)] for path and the files it \\input's or \\include's.

    LaTeX resolves a nested \\input relative to the directory it runs in (the main file's), so that
    directory is tried first and the including file's directory second. Misses go to warnings."""
    seen = seen if seen is not None else set()
    warnings = warnings if warnings is not None else []
    docs = []
    ap = os.path.abspath(path)
    if ap in seen or depth > 5:
        return docs
    seen.add(ap)
    try:
        text = read_text(path)
    except OSError as e:
        warnings.append("cannot read %s (%s)" % (path, e.strerror or e))
        return docs
    docs.append((path, text))
    if main_dir is None:
        main_dir = os.path.dirname(path)
    dirs = [main_dir]
    if os.path.abspath(os.path.dirname(path)) != os.path.abspath(main_dir):
        dirs.append(os.path.dirname(path))
    for m in re.finditer(r"\\(?:input|include)\s*\{([^{}]+)\}", strip_comments(text)):
        name = m.group(1).strip()
        if os.path.basename(name).startswith("numbers"):
            continue
        cand = resolve_input(name, dirs)
        if cand is None:
            ln = text.count("\n", 0, m.start()) + 1
            warnings.append("\\input{%s} in %s:%d not found (looked in %s)" % (
                name, os.path.basename(path), ln, ", ".join((d or ".").replace("\\", "/") for d in dirs)))
            continue
        docs.extend(read_with_inputs(cand, seen, depth + 1, main_dir, warnings))
    return docs


MACRO_DEF = re.compile(
    r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\s*\\([A-Za-z@]+)\s*\}?\s*(?:\[\d\]\s*)?"
    r"(?:\[[^\]]*\]\s*)?\{"
    r"|\\[gex]?def\s*\\([A-Za-z@]+)\s*(?:#\d\s*)*\{")
MACRO_DEF_NAME = re.compile(r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand)\*?\s*\{?\s*\\[A-Za-z@]+\s*\}?"
                            r"|\\[gex]?def\s*\\[A-Za-z@]+")


def macro_value(body):
    """Numeric value of a macro body: 0.81, $-0.35$, \\text{--}0.5, \\num{0.9876}, \\SI{12.3}{\\ms}, 81.2\\%."""
    b = re.sub(r"\\(?:num|SI|qty)\s*(?:\[[^\]]*\]\s*)?\{([^{}]*)\}(?:\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})?",
               r"\1", body)
    b = re.sub(r"\\text\{--?\}|\\textminus|\\minus|\u2212", "-", b)
    b = re.sub(r"\\(?:ensuremath|text|textrm|mathrm|textbf|mathbf|emph|textit|mathit)\b", "", b)
    cleaned = re.sub(r"\\[,;:! ]|[{}$~]|\\%|%|\\percent\b", "", b).strip().replace(",", "")
    cleaned = re.sub(r"\s+", "", cleaned)
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", cleaned):
        return float(cleaned)
    return None


def parse_numbers_file(path):
    macros = {}
    text = read_text(path)
    for m in MACRO_DEF.finditer(text):
        name = m.group(1) or m.group(2)
        o = m.end() - 1
        c = brace_span(text, o)
        body = text[o + 1:c]
        eol = text.find("\n", c)
        rest = text[c + 1: eol if eol >= 0 else len(text)]
        note = rest.split("%", 1)[1].strip() if "%" in rest else ""
        macros[name] = {"body": body.strip(), "value": macro_value(body), "source": note}
    return macros


def scan_results(results_dir, time_limit, max_mb):
    """Collect the set of numbers in each result file (sorted array per file)."""
    start = time.time()
    files, arrays = [], []
    skipped_big = 0
    total = 0
    stopped = None
    num = re.compile(rb"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
    for root, dirs, fnames in os.walk(results_dir):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for fn in sorted(fnames):
            if os.path.splitext(fn)[1].lower() not in RESULT_EXTS:
                continue
            p = os.path.join(root, fn)
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz > MAX_RESULT_FILE:
                skipped_big += 1
                continue
            if time.time() - start > time_limit or total > max_mb * 1024 * 1024:
                stopped = "time or size budget reached"
                break
            try:
                with open(p, "rb") as f:
                    content = f.read()
            except OSError:
                continue
            total += sz
            vals = set()
            for t in set(num.findall(content)):
                try:
                    vals.add(abs(float(t)))
                except ValueError:
                    pass
            files.append(os.path.relpath(p, results_dir).replace("\\", "/"))
            arrays.append(sorted(vals))
        if stopped:
            break
    return {"files": files, "arrays": arrays, "skipped_big": skipped_big,
            "bytes": total, "stopped": stopped, "seconds": time.time() - start}


def lookup(res, v, dec, percent):
    """Return the list of result files that hold a number equal to v at v's precision."""
    v = abs(v)  # the results scan stores absolute values
    cands = [(v, 0.5 * 10 ** (-dec) + 1e-12)]
    if percent:
        cands.append((v / 100.0, 0.5 * 10 ** (-dec) / 100.0 + 1e-12))
    hits = []
    for fi, arr in enumerate(res["arrays"]):
        for target, tol in cands:
            i = bisect.bisect_left(arr, target - tol)
            if i < len(arr) and arr[i] <= target + tol:
                hits.append(res["files"][fi])
                break
    return hits


def main():
    ap = argparse.ArgumentParser(description="Find literal numbers in a LaTeX paper that should be macros.")
    ap.add_argument("tex", help="main .tex file")
    ap.add_argument("--numbers", help="generated numbers file with \\newcommand definitions")
    ap.add_argument("--results-dir", help="directory of result files to cross-check (optional)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a text report")
    ap.add_argument("--all", action="store_true", help="list every literal (default lists up to 60)")
    ap.add_argument("--include-small", action="store_true", help="also report bare integers below 10")
    ap.add_argument("--include-display", action="store_true", help="also scan display equations")
    ap.add_argument("--time-limit", type=float, default=30.0, help="seconds budget for the results scan")
    ap.add_argument("--max-results-mb", type=int, default=300, help="total MB budget for the results scan")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not os.path.isfile(a.tex):
        print("ERROR: cannot read " + a.tex, file=sys.stderr)
        return 2
    warnings = []
    docs = read_with_inputs(a.tex, warnings=warnings)
    macros = {}
    if a.numbers:
        if os.path.isfile(a.numbers):
            macros = parse_numbers_file(a.numbers)
        else:
            warnings.append("numbers file not found: " + a.numbers + " (continuing without macro checks)")
    res = None
    if a.results_dir:
        if os.path.isdir(a.results_dir):
            res = scan_results(a.results_dir, a.time_limit, a.max_results_mb)
        else:
            warnings.append("results dir not found: " + a.results_dir + " (skipping results cross-check)")
    for w in warnings:
        print("WARN: " + w, file=sys.stderr)

    all_lits = []
    all_clean = ""
    for path, text in docs:
        lits, clean = find_literals(text, a.include_small, a.include_display)
        all_clean += clean + "\n"
        for l in lits:
            l["file"] = os.path.basename(path)
        all_lits.extend(lits)

    used = {}
    uses_text = MACRO_DEF_NAME.sub(" ", all_clean)
    for name in macros:
        n = len(re.findall(r"\\" + re.escape(name) + r"(?![A-Za-z@])", uses_text))
        if n:
            used[name] = n
    by_val = {}
    for name, d in macros.items():
        if d["value"] is not None:
            by_val.setdefault(round(d["value"], 9), []).append(name)

    for l in all_lits:
        l["macro_hint"] = []
        av = abs(l["value"]) if l["value"] is not None else None
        specific = (l["decimals"] >= 2 or l["kind"] == "scientific" or (av is not None and av >= 100) or
                    (l["decimals"] >= 1 and (av is not None and av >= 10 or l["kind"] == "percent" or
                                             l["where"] == "table")))
        if l["value"] is not None and macros and specific:
            v = l["value"]
            hits = list(by_val.get(round(v, 9), []))
            if l["kind"] == "percent":
                hits += by_val.get(round(v / 100.0, 9), [])
            l["macro_hint"] = hits[:3]
        l["specific"] = bool(specific)
        l["result_files"] = None
        if res is not None and l["value"] is not None and specific:
            l["result_files"] = lookup(res, l["value"], l["decimals"], l["kind"] == "percent")

    n_lit = len(all_lits)
    checked = [l for l in all_lits if l["result_files"] is not None]
    n_in_res = sum(1 for l in checked if l["result_files"])
    n_not_res = sum(1 for l in checked if not l["result_files"])
    # per paper line: does one result file hold all of that line's specific numbers?
    by_line = {}
    for l in checked:
        by_line.setdefault((l["file"], l["line"]), []).append(l)
    weak_lines = []
    for (fn, ln), group in sorted(by_line.items()):
        if len(group) < 2:
            continue
        counts = {}
        for l in group:
            for f in set(l["result_files"]):
                counts[f] = counts.get(f, 0) + 1
        best = max(counts.values()) if counts else 0
        if best < len(group):
            bf = sorted(counts, key=lambda k: -counts[k])[:1]
            weak_lines.append({"file": fn, "line": ln, "numbers": len(group), "best_file_covers": best,
                               "best_file": bf[0] if bf else None})
    n_hint = sum(1 for l in all_lits if l["macro_hint"])
    summary = {
        "tex": a.tex.replace("\\", "/"), "files_scanned": [os.path.basename(p) for p, _ in docs],
        "literal_numbers": n_lit,
        "by_where": {w: sum(1 for l in all_lits if l["where"] == w) for w in ("prose", "caption", "table", "inline-math")},
        "macros_defined": len(macros), "macros_used": len(used), "macro_uses_total": sum(used.values()),
        "literals_with_matching_macro": n_hint,
        "specific_literals_checked_against_results": len(checked) if res is not None else None,
        "literals_found_in_results": n_in_res if res is not None else None,
        "literals_not_found_in_results": n_not_res if res is not None else None,
        "lines_without_single_supporting_file": len(weak_lines) if res is not None else None,
        "warnings": warnings,
    }
    if res is not None:
        summary["results_scan"] = {"files": len(res["files"]), "mb": round(res["bytes"] / 1048576, 1),
                                   "skipped_over_2mb": res["skipped_big"], "seconds": round(res["seconds"], 1),
                                   "stopped_early": res["stopped"]}
    if a.json:
        out = {"summary": summary, "literals": all_lits, "weak_lines": weak_lines if res is not None else None,
               "unused_macros": sorted(set(macros) - set(used))}
        print(json.dumps(out, indent=2))
        return 0

    print("check_numbers report for " + summary["tex"])
    print("files scanned: " + ", ".join(summary["files_scanned"]))
    for w in warnings:
        print("WARN: " + w)
    print("literal numbers found: %d (prose %d, caption %d, table %d, inline math %d)" % (
        n_lit, summary["by_where"]["prose"], summary["by_where"]["caption"], summary["by_where"]["table"],
        summary["by_where"]["inline-math"]))
    if macros:
        print("macros defined in numbers file: %d; used in the paper: %d (%d uses)" % (
            len(macros), len(used), sum(used.values())))
        print("literals whose value equals an existing macro: %d" % n_hint)
        if n_lit and not used:
            print("FINDING: zero macro usage. Every number below is typed by hand and can go stale.")
    else:
        print("no numbers file given: macro checks skipped")
    if res is not None:
        rs = summary["results_scan"]
        print("results scan: %d files, %.1f MB, %d skipped (>2 MB), %.1fs%s" % (
            rs["files"], rs["mb"], rs["skipped_over_2mb"], rs["seconds"],
            ", stopped early" if rs["stopped_early"] else ""))
        print("specific literals (2+ decimals, 1 decimal >= 10 or in a table, e-notation, or >= 100) checked: %d; "
              "found in some result file: %d; not found: %d" % (
            len(checked), n_in_res, n_not_res))
        print("  a value found in many files is weak evidence; derived values may legitimately be absent")
        print("paper lines whose numbers no single result file supports together: %d" % len(weak_lines))
    print("")
    limit = None if a.all else 60
    print("literal numbers (file:line  where  token  hint  context):")
    ordered = sorted(all_lits, key=lambda l: (0 if l["macro_hint"] else 1))
    n_hint = sum(1 for l in all_lits if l["macro_hint"])
    if n_hint:
        print("  (%d literals equal an existing macro value and are listed first)" % n_hint)
    for i, l in enumerate(ordered):
        if limit is not None and i >= limit:
            print("... %d more (use --all or --json)" % (n_lit - limit))
            break
        hint = ""
        if l["macro_hint"]:
            hint += " macro?=" + ",".join("\\" + h for h in l["macro_hint"])
        if l["result_files"] is not None:
            rf = l["result_files"]
            if not rf:
                hint += " results=NOT-FOUND"
            elif len(rf) > 8:
                hint += " results=common-value(%d files)" % len(rf)
            else:
                hint += " results=" + ",".join(rf[:2]) + ("(+%d)" % (len(rf) - 2) if len(rf) > 2 else "")
        print("%s:%d  %-11s %s%s  | %s" % (l["file"], l["line"], l["where"], l["token"], hint, l["context"][:90]))
    if res is not None and weak_lines:
        print("")
        print("lines where no single result file holds all the line's specific numbers (check for stale or mixed sources):")
        for w in weak_lines[:25]:
            print("%s:%d  %d numbers, best file %s covers %d" % (w["file"], w["line"], w["numbers"],
                                                               w["best_file"], w["best_file_covers"]))
        if len(weak_lines) > 25:
            print("... %d more (use --json)" % (len(weak_lines) - 25))
    return 0


if __name__ == "__main__":
    sys.exit(main())
