#!/usr/bin/env python3
"""check_submission.py: pre-submission lint for a LaTeX paper folder.

Why: the cheapest rejections are mechanical: an unresolved reference, a leftover TODO, a missing
figure, an author name in a comment, a page over the limit. This script finds them in seconds.

Checks
  refs        every \\ref/\\eqref/\\cref target has a \\label (user macros such as \\figref that wrap \\ref count);
              floats never referenced are flagged
  cites       every \\cite key (natbib and biblatex forms too) exists in the .bib files; bib entries never
              cited are listed
  markers     [VERIFY], [NUM: ...], [unverified], \\cite{TODO_...}, TODO, FIXME, XXX, TBD, \\todo, ??,
              "to be completed" left in tex or bib
  figures     every \\includegraphics and \\input file exists; figure files nobody includes
  anonymity   git branch names, remote user/repo names, commit author names and e-mail names, venue
              and workshop names, repo or personal URLs, e-mail addresses, \\thanks and acknowledgements,
              "our previous work" phrasing, style-file options that switch anonymity off, PDF author field
  pages       page count of the compiled main PDF (<main>.pdf beside the main file or in build/ or out/)
              versus --venue-pages (references usually excluded; check the CFP)
  checklist   a checklist file or section is present (many venues require one)
  sections    stub sections (a heading followed by a sentence or two) and long verbatim blocks, which
              usually mean raw script output pasted into the paper
  log         undefined references and citations reported by a compile log, if one exists
  layout      overfull boxes from the compile log: text or verbatim running past the margin

Usage
  python check_submission.py paper_dir [--main main.tex] [--venue-pages 9] [--extra-terms "name1,name2"] [--json]

Exit code is 0 unless the folder cannot be read (then 2). Findings never change the exit code:
read them, then decide.
"""
import argparse
import bisect
import json
import os
import re
import subprocess
import sys

CATEGORIES = ("refs", "cites", "markers", "figures", "anonymity", "pages", "checklist", "sections", "log", "layout")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "env", "build", "_minted"}
GENERIC_BRANCHES = {"main", "master", "dev", "develop", "head", "trunk", "gh-pages", "origin"}
IMG_EXTS = ["", ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".PDF", ".PNG", ".JPG", ".pgf"]
FIG_FILE_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".pgf"}
VENUES = r"NeurIPS|NIPS|ICML|ICLR|ACL|EMNLP|NAACL|EACL|COLM|CVPR|ICCV|ECCV|AAAI|IJCAI|KDD|TMLR|COLT|AISTATS|UAI|ARR"
MARKERS = [
    (r"\[VERIFY\]", "[VERIFY] mark"),
    (r"\[NUM:", "[NUM: ...] placeholder"),
    (r"(?i)\[unverified\]", "[unverified] mark"),
    (r"\\[A-Za-z]*[Cc]ite[a-zA-Z]*\*?(?:\[[^\]]*\])*\{[^}]*\bTODO_", "\\cite{TODO_...} placeholder"),
    (r"\bTODO\b", "TODO"),
    (r"\bFIXME\b", "FIXME"),
    (r"\bXXX\b", "XXX"),
    (r"\bTBD\b", "TBD"),
    (r"\\todo\b", "\\todo"),
    (r"\[CITE\]|\[REF\]", "placeholder cite"),
    (r"\?\?", "'??' (unresolved reference?)"),
    (r"(?i)lorem ipsum", "lorem ipsum"),
    (r"(?i)\bto be (completed|written|added|filled|decided)\b", "'to be ...' placeholder"),
    (r"\bDRAFT\b|(?i:\bdraft;)", "draft marker"),
]
SELF_REF = re.compile(
    r"(?i)\b(our|we)\s+(previous|prior|earlier|recent|past)\s+(work|paper|study|studies|preprint|results|publication)|"
    r"\bwe\s+(previously|earlier)\s+(showed|proposed|introduced|reported|found|presented)\b|"
    r"\bin\s+our\s+(companion|previous|earlier)\b")


# Citation commands: LaTeX \cite and \nocite, natbib (\citet, \citep, \citeauthor, \citeyear, \Citet, ...),
# biblatex (\parencite, \textcite, \autocite, \footcite, \smartcite, \supercite, capitalised forms) and the
# biblatex multicite forms (\cites, \parencites, ...) that take several [pre][post]{keys} groups.
CITE_HEAD_RE = re.compile(r"\\((?:no|[Pp]aren|[Tt]ext|[Aa]uto|[Ff]oot|[Ff]ootfull|[Ss]mart|[Ss]uper|full)?"
                          r"[Cc]ite[a-zA-Z]*)(?![a-zA-Z@])\*?")
NOT_CITE_CMDS = {"citetext", "citestyle", "citename", "citeindexfalse", "citeindextrue"}
REF_CMDS = r"ref|eqref|autoref|Autoref|cref|Cref|pageref|nameref|vref|Vref|subref|cpageref|Cpageref|labelcref|namecref|nameCref"
REF_RE = re.compile(r"\\(?:" + REF_CMDS + r")\*?\{([^{}]*)\}")
HYPERREF_RE = re.compile(r"\\hyperref\[([^\]]*)\]")
LABEL_RE = re.compile(r"\\label\{([^{}]*)\}")
NEWCMD_RE = re.compile(r"\\(?:(?:re)?newcommand|providecommand|DeclareRobustCommand)\*?\s*"
                       r"(?:\{\s*\\([A-Za-z@]+)\s*\}|\\([A-Za-z@]+))\s*(?:\[\s*(\d)\s*\])?\s*(\[[^\]]*\])?\s*\{")
DEF_RE = re.compile(r"\\[gex]?def\s*\\([A-Za-z@]+)((?:\s*#\d)*)\s*\{")
# Words too common to flag when they come from git (a repo called "paper", a surname "Young").
COMMON_WORDS = set("""
about above after again against also always among another answer back based because been before being below
best better between both bring build came come could data deep does done down draft during each early even
every final find first from full give good great group hand have head help here high home house into just keep
kind know large last later learn left less light like line little long look made main make many might more most
much must name near need never next night note notes only open order other over page part people place plan
point public read real right said same show side since small some sound start state still such take tell than
that their them then there these they thing think this those three through time together under until upon used
very want water well were what when where which while white whole will with within word words work works world
would write year years young your
black brown green gray grey king hall wood hill field stone rose bell park ward bird fox wolf lamb cook baker
walker hunter fisher porter lane price rich bush fields
paper papers thesis article report study studies project projects research code source repo repository docs
draft drafts final submission camera ready review rebuttal workshop conference journal version release update
master develop feature branch test tests testing demo example sample misc utils tools scripts figures plots
images template latex overleaf arxiv preprint notes writeup slides poster
model models modeling modelling network networks neural learning machine deep data dataset datasets method
methods analysis experiment experiments result results system systems theory language languages vision graph
graphs robust attention transformer transformers agent agents training inference evaluation benchmark
baseline baselines performance optimization algorithm algorithms reinforcement generation prediction
classification detection segmentation representation representations embedding embeddings features sparse
dense linear random causal bayesian efficient scalable simple general novel unified adaptive dynamic
interpretability alignment safety fairness privacy security quantum physics biology chemistry medical
clinical health social human humans computer science intelligence artificial natural processing speech audio
video image text signal control robot robotics planning reasoning knowledge memory search retrieval
recommendation probing probe probes circuit circuits sparse autoencoder autoencoders feature steering
""".split())
CASE_SENSITIVE_SOURCES = ("git author name", "git author surname")
PDF_BUILD_DIRS = ("", "build", "out", "output", "_build")


class Joined:
    """A file's lines with comments stripped, joined so a regex can span lines; offsets map back to lines."""

    def __init__(self, lines):
        self.lines = lines
        code = [strip_comment(ln)[0] for ln in lines]
        self.text = "\n".join(code)
        self.starts = []
        pos = 0
        for c in code:
            self.starts.append(pos)
            pos += len(c) + 1

    def line(self, off):
        return bisect.bisect_right(self.starts, off)

    def text_at(self, off):
        return self.lines[self.line(off) - 1].strip()


def brace_end(s, i):
    """Index just after the brace group opening at s[i] == '{', or -1."""
    depth, j, n = 0, i, len(s)
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


def bracket_end(s, i, close="]"):
    """Index just after the [..] (or (..)) group opening at s[i]; braces inside are skipped. -1 if unclosed."""
    j, n, depth = i + 1, len(s), 0
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == close and depth <= 0:
            return j + 1
        j += 1
    return -1


def skip_space(s, j):
    while j < len(s) and s[j] in " \t\n":
        j += 1
    return j


def cite_groups(s, pos, multi):
    """Key groups of a citation command whose name ends at pos: [pre][post]{keys}, repeated for multicite."""
    groups = []
    j = skip_space(s, pos)
    while multi and j < len(s) and s[j] == "(":
        e = bracket_end(s, j, ")")
        if e < 0:
            return groups
        j = skip_space(s, e)
    while j < len(s):
        while j < len(s) and s[j] == "[":
            e = bracket_end(s, j)
            if e < 0:
                return groups
            j = skip_space(s, e)
        if j >= len(s) or s[j] != "{":
            break
        e = brace_end(s, j)
        if e < 0:
            break
        groups.append(s[j + 1:e - 1])
        if not multi:
            break
        j = skip_space(s, e)
        if j >= len(s) or s[j] not in "[{":
            break
    return groups


def macro_args(s, pos, info):
    """Arguments of a user macro used at s[pos:], or None when they cannot be read."""
    args = []
    j = pos
    need = info["nargs"]
    if info["default"] is not None and need:
        k = skip_space(s, j)
        if k < len(s) and s[k] == "[":
            e = bracket_end(s, k)
            if e < 0:
                return None
            args.append(s[k + 1:e - 1])
            j = e
        else:
            args.append(info["default"])
        need -= 1
    for _ in range(need):
        k = skip_space(s, j)
        if k >= len(s) or s[k] != "{":
            return None
        e = brace_end(s, k)
        if e < 0:
            return None
        args.append(s[k + 1:e - 1])
        j = e
    return args


def ref_targets(s, macros, skip=()):
    """(offset, kind, key) for \\label and \\ref-like uses in s, including uses of user macros that wrap them.
    Keys still holding a macro parameter (#1) are returned so callers can build macro templates."""
    out = []
    for m in LABEL_RE.finditer(s):
        out.append((m.start(), "label", m.group(1)))
    for m in REF_RE.finditer(s):
        for k in m.group(1).split(","):
            out.append((m.start(), "ref", k))
    for m in HYPERREF_RE.finditer(s):
        out.append((m.start(), "ref", m.group(1)))
    if macros:
        names = "|".join(sorted((re.escape(n) for n in macros), key=len, reverse=True))
        for m in re.finditer(r"\\(" + names + r")(?![A-Za-z@])", s):
            if any(a <= m.start() < b for a, b in skip):
                continue
            info = macros[m.group(1)]
            args = macro_args(s, m.end(), info)
            if args is None:
                continue
            for kind, tpl in info["targets"]:
                key = re.sub(r"#(\d)", lambda x: args[int(x.group(1)) - 1] if int(x.group(1)) <= len(args) else "", tpl)
                for k in (key.split(",") if kind == "ref" else [key]):
                    out.append((m.start(), kind, k))
    return [(o, kind, k.strip()) for o, kind, k in out if k.strip()]


def ref_macros(texts):
    """{name: info} for \\newcommand/\\def macros whose body holds \\ref{#1}, \\cref{#1}, \\label{#1} and
    the like (also through another such macro), and {text index: [(start, end)]} of the definitions."""
    defs, spans = [], {}
    for idx, s in enumerate(texts):
        for m in NEWCMD_RE.finditer(s):
            e = brace_end(s, m.end() - 1)
            if e < 0:
                continue
            default = m.group(4)[1:-1] if m.group(4) else None
            defs.append((m.group(1) or m.group(2), int(m.group(3) or 0), default, s[m.end():e - 1]))
            spans.setdefault(idx, []).append((m.start(), e))
        for m in DEF_RE.finditer(s):
            e = brace_end(s, m.end() - 1)
            if e < 0:
                continue
            defs.append((m.group(1), m.group(2).count("#"), None, s[m.end():e - 1]))
            spans.setdefault(idx, []).append((m.start(), e))
    # redefining \\ref or \\label itself is already covered by the plain patterns
    defs = [d for d in defs if not re.fullmatch(r"(?:" + REF_CMDS + r"|label|hyperref)", d[0])]
    macros = {}
    for _ in range(3):
        changed = False
        for name, nargs, default, body in defs:
            known = {k: v for k, v in macros.items() if k != name}
            targets = sorted({(kind, k) for _, kind, k in ref_targets(body, known) if "#" in k})
            if targets and (name not in macros or macros[name]["targets"] != targets):
                macros[name] = {"nargs": nargs, "default": default, "targets": targets}
                changed = True
        if not changed:
            break
    return macros, spans


def bib_split(lines):
    """(code, comment) per line of a .bib file. A % there is literal (URLs hold %20); a line is a comment
    only when it starts with % outside any entry."""
    out, depth = [], 0
    for ln in lines:
        if depth <= 0 and ln.lstrip().startswith("%"):
            out.append(("", ln))
            continue
        out.append((ln, ""))
        i = 0
        while i < len(ln):
            c = ln[i]
            if c == "\\":
                i += 2
                continue
            depth += (c == "{") - (c == "}")
            i += 1
        depth = max(depth, 0)
    return out


def pdf_string(tok):
    """Decode a PDF literal (...) or hex <...> string, including UTF-16 with a FEFF byte-order mark."""
    if tok[:1] == b"<":
        h = re.sub(rb"\s+", b"", tok[1:-1])
        if len(h) % 2:
            h += b"0"
        try:
            data = bytes.fromhex(h.decode("ascii"))
        except ValueError:
            return ""
    else:
        body, data, i = tok[1:-1], bytearray(), 0
        esc = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
        while i < len(body):
            c = body[i:i + 1]
            if c == b"\\" and i + 1 < len(body):
                nxt = body[i + 1:i + 2]
                om = re.match(rb"[0-7]{1,3}", body[i + 1:i + 4])
                if om:
                    data.append(int(om.group(0), 8) & 0xFF)
                    i += 1 + len(om.group(0))
                    continue
                data += esc.get(nxt, nxt if nxt not in b"\r\n" else b"")
                i += 2
                continue
            data += c
            i += 1
        data = bytes(data)
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", "replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", "replace")
    return data.decode("latin-1")


def common_word(term):
    """True for git-derived strings that are ordinary words (or made only of ordinary words)."""
    parts = [p for p in re.split(r"[-_.\s]+", term.lower()) if p]
    if not parts:
        return True
    return all(len(p) < 4 or p in COMMON_WORDS or (p.endswith("s") and p[:-1] in COMMON_WORDS) for p in parts)


STUB_WORDS = 40
VERBATIM_LINES = 30
SECTION_RE = re.compile(r"\\(section|subsection)\*?(?:\[[^\]]*\])?\{([^{}]*)\}")


def prose_words(chunk):
    """Rough count of prose words in a LaTeX chunk (math, commands and braces removed)."""
    t = re.sub(r"\$[^$]*\$", " ", chunk)
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", t)
    return len(re.findall(r"[A-Za-z]{2,}", t))


def section_issues(lines):
    """(line, kind, detail) for stub sections and long verbatim blocks in one file."""
    code = [strip_comment(ln)[0] for ln in lines]
    out = []
    heads = []
    for i, ln in enumerate(code, 1):
        m = SECTION_RE.search(ln)
        if m:
            heads.append((i, m.group(1), m.group(2).strip(), m.end()))
    for k, (i, kind, title, col) in enumerate(heads):
        nxt = heads[k + 1] if k + 1 < len(heads) else None
        if nxt and kind == "section" and nxt[1] == "subsection":
            continue  # the text lives in the subsections
        stop = nxt[0] - 1 if nxt else len(code)
        body = "\n".join([code[i - 1][col:]] + code[i:stop])
        body = re.split(r"\\end\{document\}|\\bibliography(?:style)?\{|\\printbibliography|\\appendix\b", body)[0]
        if re.search(r"\\(?:input|include|includegraphics|begin\{(?:figure|table|tabular|verbatim|lstlisting|"
                     r"algorithm|equation|align|itemize|enumerate))", body):
            continue
        n = prose_words(body)
        if n < STUB_WORDS:
            out.append((i, "stub", "%s '%s' has %d words of text; deliver what the heading promises or cut it" %
                        (kind, title, n)))
    start = None
    for i, ln in enumerate(code, 1):
        if re.search(r"\\begin\{(?:verbatim|Verbatim|lstlisting|minted|alltt)\}", ln):
            start = i
        elif start and re.search(r"\\end\{(?:verbatim|Verbatim|lstlisting|minted|alltt)\}", ln):
            if i - start - 1 >= VERBATIM_LINES:
                out.append((start, "verbatim", "verbatim block of %d lines; raw script output belongs in the "
                            "released code, with a pointer in the paper" % (i - start - 1)))
            start = None
    return out


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def strip_comment(line):
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if c == "\\":
            i += 2
            continue
        if c == "%":
            return line[:i], line[i:]
        i += 1
    return line, ""


def list_files(root, exts):
    out = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if os.path.splitext(f)[1].lower() in exts:
                out.append(os.path.join(r, f))
    return sorted(out)


def rel(root, p):
    return os.path.relpath(p, root).replace("\\", "/")


def git(dirpath, *args):
    try:
        r = subprocess.run(["git", "-C", dirpath] + list(args), capture_output=True, text=True, timeout=15)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def git_terms(paper_dir):
    """Return {term: source} of repo-derived strings that should not appear in an anonymous submission.
    Ordinary words (a repo called "paper", a surname "Young") are left out: they would flag every normal use."""
    terms = {}
    top = git(paper_dir, "rev-parse", "--show-toplevel").strip()
    if not top:
        return terms, None

    def put(term, why):
        term = term.strip()
        if len(term) >= 4 and term not in terms and not common_word(term):
            terms[term] = why
    for b in git(top, "branch", "-a", "--format=%(refname:short)").splitlines():
        b = b.strip().split("/", 1)[-1] if b.strip().startswith("origin/") else b.strip()
        if b and "HEAD" not in b and b.lower() not in GENERIC_BRANCHES:
            put(b, "git branch")
    for line in git(top, "remote", "-v").splitlines():
        m = re.search(r"[:/]([^/:]+)/([^/\s]+?)(?:\.git)?\s", line + " ")
        if m:
            put(m.group(1), "git remote user/org")
            put(m.group(2), "git remote repo name")
    put(os.path.basename(top), "repository folder name")
    seen = set()
    for line in git(top, "log", "--format=%an|%ae").splitlines():
        if line in seen:
            continue
        seen.add(line)
        name, _, email = line.partition("|")
        name = name.strip()
        if len(name) >= 5 and " " in name and not re.search(r"(?i)your_|example|bot\b", name):
            terms.setdefault(name, "git author name")  # a full name is specific even when its parts are words
            if len(name.split()[-1]) >= 5:
                put(name.split()[-1], "git author surname")
        local = email.split("@")[0]
        if len(local) >= 6 and not re.search(r"(?i)your_|example|noreply", local):
            put(local, "git author e-mail name")
    return terms, top


def main():
    ap = argparse.ArgumentParser(description="Pre-submission lint for a LaTeX paper folder.")
    ap.add_argument("paper_dir", help="folder holding the .tex, .bib and figures")
    ap.add_argument("--main", help="main .tex file name (default: auto-detect)")
    ap.add_argument("--venue-pages", type=int, help="page limit from the call for papers")
    ap.add_argument("--extra-terms", help="comma-separated extra strings to grep for in the anonymity check")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    root = a.paper_dir
    if not os.path.isdir(root):
        print("ERROR: not a folder: " + root, file=sys.stderr)
        return 2
    tex_files = list_files(root, {".tex"})
    bib_files_all = list_files(root, {".bib"})
    if not tex_files:
        print("ERROR: no .tex files under " + root, file=sys.stderr)
        return 2
    main_tex = None
    if a.main:
        cand = os.path.join(root, a.main)
        main_tex = cand if os.path.isfile(cand) else None
        if not main_tex:
            print("WARN: --main %s not found under %s; auto-detecting the main file instead" % (a.main, root), file=sys.stderr)
    if not main_tex:
        with_class = [p for p in tex_files if "\\documentclass" in read_text(p)]
        pref = [p for p in with_class if os.path.basename(p).lower() == "main.tex"]
        main_tex = (pref or with_class or tex_files)[0]

    hits = []

    def add(cat, sev, msg, file=None, line=None, text=None):
        hits.append({"category": cat, "severity": sev, "file": file, "line": line, "msg": msg, "text": (text or "")[:110]})

    src = {}
    for p in tex_files:
        src[p] = read_text(p).split("\n")

    # ---- refs (on comment-stripped text joined across lines, so a group split over two lines still counts)
    joined = {p: Joined(lines) for p, lines in src.items()}
    texts = [joined[p].text for p in tex_files]
    sty_texts = [Joined(read_text(q).split("\n")).text for q in list_files(root, {".sty"})]
    macros, def_spans = ref_macros(texts + sty_texts)
    labels, ref_uses = {}, {}
    for idx, p in enumerate(tex_files):
        jt = joined[p]
        for off, kind, k in sorted(ref_targets(jt.text, macros, def_spans.get(idx, ()))):
            if "#" in k:
                continue  # a macro parameter inside a definition, not a label
            if kind == "label":
                labels.setdefault(k, (rel(root, p), jt.line(off)))
            else:
                ref_uses.setdefault(k, []).append((rel(root, p), jt.line(off), jt.text_at(off)))
    for k, uses in sorted(ref_uses.items()):
        if k not in labels:
            f, i, t = uses[0]
            add("refs", "error", "\\ref to undefined label '%s' (%d use(s))" % (k, len(uses)), f, i, t)
    for k, (f, i) in sorted(labels.items()):
        if k not in ref_uses and re.match(r"(fig|tab|table|figure|alg|eq|sec|app|thm|lem)[:_-]", k, re.I):
            sev = "warn" if re.match(r"(fig|tab|table|figure|alg)", k, re.I) else "info"
            add("refs", sev, "label '%s' is never referenced in the text" % k, f, i)

    # ---- bib / cites
    bib_names = []
    for p, lines in src.items():
        for ln in lines:
            code, _ = strip_comment(ln)
            for m in re.finditer(r"\\bibliography\{([^{}]*)\}|\\addbibresource(?:\[[^\]]*\])?\{([^{}]*)\}", code):
                for k in (m.group(1) or m.group(2)).split(","):
                    k = k.strip()
                    if k:
                        bib_names.append(k if k.endswith(".bib") else k + ".bib")
    bib_paths = []
    for b in bib_names:
        for cand in [os.path.join(os.path.dirname(main_tex), b), os.path.join(root, b)]:
            if os.path.isfile(cand):
                bib_paths.append(cand)
                break
        else:
            add("cites", "error", "bibliography file '%s' named in the tex is not found" % b)
    if not bib_names:
        bib_paths = bib_files_all
        if not bib_paths:
            add("cites", "info", "no \\bibliography or .bib file found (fine if the paper uses an inline thebibliography)")
    bib_keys = {}
    for bp in bib_paths:
        txt = read_text(bp)
        for m in re.finditer(r"@\s*([A-Za-z]+)\s*[{(]\s*([^,\s]+)\s*,", txt):
            if m.group(1).lower() in ("comment", "string", "preamble"):
                continue
            bib_keys.setdefault(m.group(2), (rel(root, bp), txt.count("\n", 0, m.start()) + 1))
    cited, nocite_all = {}, False
    for p in tex_files:
        jt = joined[p]
        for m in CITE_HEAD_RE.finditer(jt.text):
            name = m.group(1)
            if name in NOT_CITE_CMDS:
                continue
            for grp in cite_groups(jt.text, m.end(), name.endswith("cites")):
                for k in grp.split(","):
                    k = k.strip()
                    if not k or "#" in k:
                        continue
                    if k == "*" and name == "nocite":
                        nocite_all = True
                    else:
                        cited.setdefault(k, (rel(root, p), jt.line(m.start()), jt.text_at(m.start())))
    if bib_keys or bib_paths:
        for k, (f, i, t) in sorted(cited.items()):
            if k not in bib_keys:
                add("cites", "error", "\\cite key '%s' is not in any .bib file" % k, f, i, t)
        if not nocite_all:
            for k, (f, i) in sorted(bib_keys.items()):
                if k not in cited:
                    add("cites", "warn", "bib entry '%s' is never cited (the bibliography style hides it, but clean it before sharing the source)" % k, f, i)

    # ---- markers (tex and bib)
    def code_comment(p, lines):
        if p.lower().endswith(".bib"):
            return bib_split(lines)
        return [strip_comment(ln) for ln in lines]

    for p in tex_files + bib_files_all:
        lines = src[p] if p in src else read_text(p).split("\n")
        for i, (ln, (code, comment)) in enumerate(zip(lines, code_comment(p, lines)), 1):
            for pat, name in MARKERS:
                if re.search(pat, code):
                    add("markers", "warn", "%s left in text" % name, rel(root, p), i, ln.strip())
                elif comment and re.search(pat, comment) and "VERIFY" not in name:
                    add("markers", "info", "%s in a comment" % name, rel(root, p), i, ln.strip())

    # ---- figures and inputs
    gpaths = [""]
    for lines in src.values():
        for ln in lines:
            code, _ = strip_comment(ln)
            m = re.search(r"\\graphicspath\{((?:\{[^{}]*\})+)\}", code)
            if m:
                gpaths += re.findall(r"\{([^{}]*)\}", m.group(1))
    used_files = set()
    main_dir = os.path.dirname(main_tex)
    for p, lines in src.items():
        base = os.path.dirname(p)
        for i, ln in enumerate(lines, 1):
            code, _ = strip_comment(ln)
            for m in re.finditer(r"\\includegraphics\*?(?:\[[^\]]*\])?\{([^{}]*)\}", code):
                name = m.group(1).strip()
                found = None
                for gp in gpaths:
                    for ext in IMG_EXTS:
                        for b in (main_dir, base, root):
                            cand = os.path.normpath(os.path.join(b, gp, name + ext))
                            if os.path.isfile(cand):
                                found = cand
                                break
                        if found:
                            break
                    if found:
                        break
                if found:
                    used_files.add(os.path.normpath(found))
                else:
                    add("figures", "error", "figure file not found: " + name, rel(root, p), i, ln.strip())
            for m in re.finditer(r"\\(?:input|include|subfile)\{([^{}]*)\}", code):
                name = m.group(1).strip()
                # LaTeX resolves \\input against the directory it was run from (the main file's), so a nested
                # \\input{sections/b} inside sections/a.tex means <main dir>/sections/b.tex
                cands = [os.path.join(b, name + ext) for b in (main_dir, base, root) for ext in ("", ".tex")]
                if not any(os.path.isfile(c) for c in cands):
                    add("figures", "error", "\\input file not found: " + name, rel(root, p), i, ln.strip())
    fig_dirs = [d for d in (os.path.join(root, n) for n in ("figures", "figs", "fig", "images", "img")) if os.path.isdir(d)]
    unused = []
    for d in fig_dirs:
        for fp in list_files(d, FIG_FILE_EXTS):
            if os.path.normpath(fp) not in used_files:
                unused.append(rel(root, fp))
    if unused:
        add("figures", "info", "%d figure file(s) in figure folders are not included by any \\includegraphics: %s%s" % (
            len(unused), ", ".join(unused[:8]), " ..." if len(unused) > 8 else ""))
    n_fig = len(used_files)

    # ---- anonymity
    terms, top = git_terms(root)
    if a.extra_terms:
        for t in a.extra_terms.split(","):
            if t.strip():
                terms[t.strip()] = "user-supplied term"
    # .sty and .cls files are left out: official venue style files carry the venue name and contact e-mails
    scan_files = tex_files + list_files(root, {".bib", ".bbl"})
    # person names are matched case-sensitively ("Young" the author, not "young" the adjective)
    term_res = {t: (re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])",
                               0 if why in CASE_SENSITIVE_SOURCES else re.I), why) for t, why in terms.items()}
    venue_re = re.compile(r"\b(" + VENUES + r")\b(?:[\s-]*(?:20)?\d{2,4})?")
    pat_misc = [
        (re.compile(r"github\.com|gitlab\.com|bitbucket\.org|huggingface\.co/[A-Za-z0-9_-]+|osf\.io|zenodo\.org"), "code or data host URL (links to your account de-anonymise)"),
        (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "e-mail address"),
        (re.compile(r"\\thanks\b|\\email\b|\\affil\b|\\affiliation\b|\\institute\b|pdfauthor"), "author, affiliation or thanks command"),
        (re.compile(r"(?i)\\(sub)?section\*?\{acknowledg"), "acknowledgements section (remove for review)"),
        (SELF_REF, "self-referencing phrase that signals authorship"),
        (re.compile(r"\\usepackage\[[^\]]*\b(preprint|final|accepted|camera)\b[^\]]*\]\{[^}]*\}|\\documentclass\[[^\]]*\b(final|accepted|camera)\b[^\]]*\]"),
         "style option that may switch anonymity or line numbers off (check the venue instructions)"),
    ]
    for p in scan_files:
        lines = src[p] if p in src else read_text(p).split("\n")
        is_bib = p.lower().endswith((".bib", ".bbl"))
        for i, (ln, (code, comment)) in enumerate(zip(lines, code_comment(p, lines)), 1):
            for term, (rx, why) in term_res.items():
                if rx.search(ln):
                    in_c = bool(comment) and bool(rx.search(comment)) and not rx.search(code)
                    add("anonymity", "warn", "%s '%s' appears%s" % (why, term, " in a comment" if in_c else ""),
                        rel(root, p), i, ln.strip())
            if is_bib:
                continue
            for m in venue_re.finditer(ln):
                in_c = bool(comment) and m.start() >= len(code)
                add("anonymity", "warn" if in_c else "info",
                    "venue or workshop name '%s'%s" % (m.group(0).strip(), " in a comment (comments ship with the source)" if in_c else " in text (fine as a citation, check it is not a self-identifying hint)"),
                    rel(root, p), i, ln.strip())
            for pat, why in pat_misc:
                m = pat.search(ln)
                if m:
                    in_c = bool(comment) and m.start() >= len(code)
                    add("anonymity", "warn", why + (" (in a comment)" if in_c else ""), rel(root, p), i, ln.strip())
    # author block content
    mt = read_text(main_tex)
    m = re.search(r"\\author\s*(?:\[[^\]]*\])?\{", mt)
    if m:
        depth, j = 1, m.end()
        while j < len(mt) and depth:
            depth += (mt[j] == "{") - (mt[j] == "}")
            j += 1
        block = mt[m.end():j - 1]
        block = re.sub(r"\\thanks\{[^{}]*\}|%[^\n]*", "", block)
        if not re.search(r"(?i)anonym", block) and re.sub(r"[\s\\&{}]|\\\\", "", block):
            add("anonymity", "warn", "\\author block does not say Anonymous: " + re.sub(r"\s+", " ", block).strip()[:60],
                rel(root, main_tex), mt.count("\n", 0, m.start()) + 1)

    # ---- PDF and pages
    # only the main file's own PDF counts: <stem>.pdf next to it or in a build/out folder beside it (a figure
    # PDF such as plots/loss_curve.pdf is not the paper)
    stem = os.path.splitext(os.path.basename(main_tex))[0]
    pdf_dirs = []
    for d in (os.path.dirname(main_tex), root):
        for sub in PDF_BUILD_DIRS:
            c = os.path.normpath(os.path.join(d, sub))
            if c not in pdf_dirs:
                pdf_dirs.append(c)
    same = [c for c in (os.path.join(d, stem + ".pdf") for d in pdf_dirs) if os.path.isfile(c)]
    pdf = max(same, key=os.path.getmtime) if same else None
    pages = None
    if pdf:
        pages, how = count_pdf_pages(pdf)
        if pages:
            msg = "%s: %d page(s) (%s)" % (rel(root, pdf), pages, how)
            if a.venue_pages and pages > a.venue_pages:
                add("pages", "warn", msg + "; over the %d-page limit (check whether references and appendix are excluded)" % a.venue_pages)
            else:
                add("pages", "info", msg + ("; limit %d" % a.venue_pages if a.venue_pages else ""))
        else:
            add("pages", "info", "could not count pages in " + rel(root, pdf))
        try:
            with open(pdf, "rb") as fh:
                raw = fh.read(4000000)
            am = re.search(rb"/Author\s*(\((?:\\.|[^\\)]){0,400}\)|<[0-9A-Fa-f\s]{0,1600}>)", raw, re.S)
            author = pdf_string(am.group(1)).strip() if am else ""
            if author:
                add("anonymity", "warn", "PDF metadata Author field is set: " + author[:80])
        except OSError:
            pass
    else:
        add("pages", "info", "no compiled PDF found (looked for %s.pdf next to the main file and in build/ or out/); "
            "compile and rerun to check the page count" % stem + ("" if a.venue_pages else " (give --venue-pages)"))

    # ---- sections: stubs and pasted output
    for p, lines in src.items():
        for i, kind, msg in section_issues(lines):
            add("sections", "warn", msg, rel(root, p), i, lines[i - 1].strip())

    # ---- checklist
    chk = [p for p in list_files(root, {".tex", ".md", ".txt", ".pdf"}) if re.search(r"(?i)checklist", os.path.basename(p))]
    in_text = any(re.search(r"(?i)paper checklist|reproducibility checklist|responsible nlp", read_text(p)) for p in tex_files)
    if chk or in_text:
        add("checklist", "info", "checklist found: " + (", ".join(rel(root, p) for p in chk[:3]) or "section inside the tex"))
    else:
        add("checklist", "warn", "no checklist file or section found; many venues require one (see the call for papers)")

    # ---- compile log
    logp = os.path.splitext(main_tex)[0] + ".log"
    if os.path.isfile(logp):
        lg = read_text(logp)
        und = len(re.findall(r"LaTeX Warning: (?:Reference|Citation) `[^']*' .*undefined", lg))
        ovf = re.findall(r"Overfull \\hbox \(([0-9.]+)pt too wide\) (?:in paragraph|detected) at lines? ([0-9]+)", lg)
        add("log", "warn" if und else "info", "compile log: %d undefined reference/citation warning(s), %d overfull hbox" % (und, len(ovf)))
        wide = sorted(((float(w), int(l)) for w, l in ovf if float(w) > 10.0), reverse=True)
        for w, l in wide[:10]:
            add("layout", "warn", "overfull hbox %.0fpt too wide (the log names source line %d of the file being "
                "typeset): text runs past the margin" % (w, l))
        if len(wide) > 10:
            add("layout", "warn", "%d more overfull boxes wider than 10pt" % (len(wide) - 10))
    else:
        add("layout", "info", "no compile log next to the main file; text running past the margin was not checked")

    manual = ["LLM-use disclosure: not machine-checkable; follow the venue policy",
              "page limit, margins and font: confirm against the official call for papers (record URL and date)",
              "supplementary files and code links: confirm they are anonymised too",
              "render every page of the PDF and look at it: clipped figure text, tables or verbatim past the margin, empty sections",
              "read the PDF aloud once; fresh-reader pass before upload"]

    counts = {}
    for h in hits:
        counts.setdefault(h["category"], {"error": 0, "warn": 0, "info": 0})[h["severity"]] += 1
    summary = {"paper_dir": root.replace("\\", "/"), "main_tex": rel(root, main_tex), "tex_files": len(tex_files),
               "bib_files": [rel(root, b) for b in bib_paths], "labels": len(labels), "bib_entries": len(bib_keys),
               "cited_keys": len(cited), "figures_included": n_fig, "pdf_pages": pages,
               "git_repo": bool(top), "anonymity_terms_from_git": len([t for t, s in terms.items() if s.startswith("git") or "repository" in s]),
               "counts": counts}
    if a.json:
        print(json.dumps({"summary": summary, "findings": hits, "manual_checks": manual}, indent=2))
        return 0

    print("check_submission report for " + summary["paper_dir"])
    print("main file: %s   tex files: %d   bib: %s" % (summary["main_tex"], len(tex_files), ", ".join(summary["bib_files"]) or "none"))
    print("labels %d, bib entries %d, distinct cited keys %d, figure files included %d, PDF pages %s" % (
        len(labels), len(bib_keys), len(cited), n_fig, pages if pages else "n/a"))
    print("git repo: %s; repo-derived anonymity terms: %d" % ("yes" if top else "no", summary["anonymity_terms_from_git"]))
    print("")
    print("%-10s %6s %6s %6s" % ("category", "error", "warn", "info"))
    for cat in CATEGORIES:
        c = counts.get(cat, {"error": 0, "warn": 0, "info": 0})
        print("%-10s %6d %6d %6d" % (cat, c["error"], c["warn"], c["info"]))
    for cat in CATEGORIES:
        items = [h for h in hits if h["category"] == cat]
        if not items:
            print("\n[%s] clean" % cat)
            continue
        print("\n[%s]" % cat)
        order = {"error": 0, "warn": 1, "info": 2}
        for h in sorted(items, key=lambda x: order[x["severity"]])[:25]:
            loc = (" %s:%s" % (h["file"], h["line"] if h["line"] else "")) if h["file"] else ""
            print("  %-5s%s  %s" % (h["severity"].upper(), loc, h["msg"]))
            if h["text"] and h["severity"] != "info":
                print("         | " + h["text"])
        if len(items) > 25:
            print("  ... %d more (use --json)" % (len(items) - 25))
    print("\nmanual checks (cannot be automated):")
    for m_ in manual:
        print("  - " + m_)
    return 0


def count_pdf_pages(path):
    """Count pages with a regex over plain and Flate-compressed objects. Return (pages, method)."""
    import zlib
    try:
        with open(path, "rb") as fh:
            raw = fh.read(60 * 1024 * 1024)
    except OSError:
        return None, ""
    n = len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", raw))
    counts = [int(x) for x in re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", raw)]
    counts += [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", raw)]
    if n or counts:
        return max([n] + counts), "page objects" if n >= (max(counts) if counts else 0) else "/Count"
    total_page, total_count = 0, []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        try:
            d = zlib.decompress(m.group(1))
        except Exception:
            continue
        total_page += len(re.findall(rb"/Type\s*/Page(?![A-Za-z])", d))
        total_count += [int(x) for x in re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", d)]
        total_count += [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", d)]
    if total_page or total_count:
        return max([total_page] + total_count), "compressed object streams"
    return None, ""


if __name__ == "__main__":
    sys.exit(main())
