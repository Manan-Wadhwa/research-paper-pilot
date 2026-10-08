#!/usr/bin/env python3
"""check_numbers.py: find literal numbers in a LaTeX paper that should come from a numbers file.

Why: a number typed by hand goes stale the moment a result file regenerates. A paper
whose prose pulls every figure from a generated macro (\\newcommand{\\accA}{0.81}) cannot drift.

What it does
  1. Scans prose, captions and inline math of the .tex file (and files it \\input's) for
     literal numbers. It ignores labels, refs, cite keys, dimensions, years, model-size
     tokens, layer-style names (L31, H28), "Figure 3" style references, display equations
     and the preamble.
  2. With --numbers, reads macro definitions from the numbers file, counts how many of them the
     paper actually uses, and suggests a macro for any literal whose value matches one.
  3. With --results-dir, checks whether each literal appears (after rounding) in any .txt, .csv,
     .json or .md result file under 2 MB. Not finding a number is a prompt to look, not proof of error:
     derived values (ratios, percentages) often live in no single file.

Usage
  python check_numbers.py paper/main.tex [--numbers paper/numbers.tex] [--results-dir results]
                          [--json] [--all] [--include-small] [--include-display]

Exit code is 0 unless the tex file cannot be read (then 2).
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
    r"(?P<sci>\d+(?:\.\d+)?\s*(?:\\times|\\cdot)\s*10\^\{?[-+]?\d+\}?|10\^\{?[-+]?\d+\}?)"
    r"|(?P<num>\d{1,3}(?:(?:\{,\}|,)\d{3})+(?!\d)(?:\.\d+)?|\d+(?:\.\d+)?)"
)

MASK_PATTERNS = [
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
REF_PREFIX = re.compile(
    r"(?:Figure|Figures|Fig\.?|Table|Tables|Tab\.?|Section|Sec\.?|Sections|Eq\.?|Eqs\.?|Equation|Appendix|Algorithm|"
    r"Alg\.?|Theorem|Lemma|Proposition|Corollary|Page|pp?\.|Line|Step|Panel|Box|\\S|\\P|Chapter|Ch\.?)"
    r"[\s~\\]*(?:\\,)?$")


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
    for m in re.finditer(r"\\\[.*?\\\]", text, re.S):
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
    return sorted(disp), sorted(inl)


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
    return sorted(out)


def num_value(token):
    t = token.replace("{,}", "").replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


def decimals_of(token):
    t = token.replace("{,}", "").replace(",", "")
    return len(t.split(".")[1]) if "." in t else 0


def find_literals(text, include_small, include_display):
    clean = strip_comments(text)
    masked = mask_spans(clean)
    caps = caption_spans(clean)
    disp, inl = classify_regions(clean)
    tabs = table_intervals(clean)
    line_starts = [0] + [m.end() for m in re.finditer(r"\n", clean)]
    lits = []
    for m in NUM_RE.finditer(masked):
        s, e = m.start(), m.end()
        tok = m.group(0)
        kind = "number"
        if m.group("sci"):
            kind = "scientific"
        before = masked[max(0, s - 24):s]
        after = masked[e:e + 3]
        prev = masked[s - 1] if s > 0 else " "
        if kind == "number":
            if prev.isalpha() or prev in "_\\" or (prev == "-" and s > 1 and masked[s - 2].isalpha()):
                continue
            if after[:1].isalpha() and after[:1] not in "kx":
                continue
            if after[:1] == "_":
                continue
            if REF_PREFIX.search(before):
                continue
            if after.startswith("\\%") or after.startswith("%") or re.match(r"\s*percent", masked[e:e + 9]):
                kind = "percent"
            val = num_value(tok)
            if val is None:
                continue
            if kind == "number" and "." not in tok and "," not in tok and "{" not in tok:
                if 1900 <= val <= 2100:
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
        pre = masked[max(0, s - 4):s]
        if pre.endswith("--") or pre.endswith("–"):
            sign = ""
        elif pre.endswith("{-}") or (pre.endswith("-") and not (s > 1 and masked[s - 2].isalnum())):
            sign = "-"
        elif pre.endswith("{+}") or pre.endswith("+"):
            sign = "+"
        ln = bisect.bisect_right(line_starts, s)
        ctx = re.sub(r"\s+", " ", clean[max(0, s - 40):e + 40]).strip()
        lits.append({"line": ln, "token": sign + tok + ("%" if kind == "percent" else ""),
                     "value": None if kind == "scientific" else num_value(tok),
                     "decimals": decimals_of(tok) if kind != "scientific" else 0,
                     "kind": kind, "where": where, "context": ctx})
    return lits, clean


def read_with_inputs(path, seen=None, depth=0):
    seen = seen if seen is not None else set()
    docs = []
    ap = os.path.abspath(path)
    if ap in seen or depth > 5:
        return docs
    seen.add(ap)
    try:
        text = read_text(path)
    except OSError:
        return docs
    docs.append((path, text))
    base = os.path.dirname(path)
    for m in re.finditer(r"\\(?:input|include)\{([^{}]+)\}", strip_comments(text)):
        name = m.group(1).strip()
        cand = os.path.join(base, name)
        if not cand.endswith(".tex"):
            cand += ".tex"
        if os.path.isfile(cand) and not os.path.basename(cand).startswith("numbers"):
            docs.extend(read_with_inputs(cand, seen, depth + 1))
    return docs


def parse_numbers_file(path):
    macros = {}
    text = read_text(path)
    pat = r"\\(?:newcommand|renewcommand|providecommand)\*?\s*\{?\\([A-Za-z@]+)\}?\s*(?:\[\d\])?\s*\{"
    for m in re.finditer(pat, text):
        name = m.group(1)
        o = m.end() - 1
        c = brace_span(text, o)
        body = text[o + 1:c]
        eol = text.find("\n", c)
        rest = text[c + 1: eol if eol >= 0 else len(text)]
        note = rest.split("%", 1)[1].strip() if "%" in rest else ""
        cleaned = re.sub(r"\\[,;:! ]|[{}$]|\\%|%", "", body).strip().replace(",", "")
        val = None
        if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", cleaned):
            val = float(cleaned)
        macros[name] = {"body": body.strip(), "value": val, "source": note}
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
    docs = read_with_inputs(a.tex)
    macros = {}
    if a.numbers:
        if os.path.isfile(a.numbers):
            macros = parse_numbers_file(a.numbers)
        else:
            print("WARN: numbers file not found: " + a.numbers + " (continuing without macro checks)")
    res = None
    if a.results_dir:
        if os.path.isdir(a.results_dir):
            res = scan_results(a.results_dir, a.time_limit, a.max_results_mb)
        else:
            print("WARN: results dir not found: " + a.results_dir + " (skipping results cross-check)")

    all_lits = []
    all_clean = ""
    for path, text in docs:
        lits, clean = find_literals(text, a.include_small, a.include_display)
        all_clean += clean + "\n"
        for l in lits:
            l["file"] = os.path.basename(path)
        all_lits.extend(lits)

    used = {}
    uses_text = re.sub(r"\\(?:re|provide)?(?:new)?command\*?\s*\{?\\[A-Za-z@]+\}?", " ", all_clean)
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
        specific = l["decimals"] >= 2 or (l["value"] is not None and l["value"] >= 100) or             (l["kind"] == "percent" and l["decimals"] >= 1)
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
        print("specific literals (2+ decimals, or >= 100) checked: %d; found in some result file: %d; not found: %d" % (
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
