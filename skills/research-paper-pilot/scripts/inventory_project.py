#!/usr/bin/env python3
"""Inventory a research project directory so a newcomer can see what exists.

Collects, in one pass: a depth-limited file tree, a git summary (commits,
authors, dates, branches, remotes, untracked paths), a dated commit list,
a results inventory, provenance sidecar counts, candidate key documents,
results folders that no document mentions (orphans) and documents that
files or commit messages mention but that are absent on disk.

Stdlib only. Run it with `python`. The report is markdown; --json prints the
same data as JSON on stdout. A missing git or an unreadable file produces a
one-line WARN and the run continues.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

PRUNE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "env", "__pycache__",
    ".ipynb_checkpoints", ".mypy_cache", ".pytest_cache", ".tox",
    "site-packages", ".idea", ".vscode",
}
TEXT_EXTS = {".md", ".tex", ".txt", ".rst"}
DOC_EXTS = {"md", "tex", "bib", "pdf", "txt", "html", "ipynb", "rst"}
MENTION_EXTS = DOC_EXTS | {"json", "jsonl", "csv", "py", "yaml", "yml", "sh", "toml", "npy", "pt"}
MAX_FILES = 400000
MAX_TEXT_BYTES = 2 * 1024 * 1024
KEY_DOC_PATTERNS = [
    ("readme", re.compile(r"^readme", re.I)),
    ("results", re.compile(r"^results?[_\-.]", re.I)),
    ("claims", re.compile(r"^claims?[_\-.]", re.I)),
    ("project", re.compile(r"^project[_\-.]", re.I)),
    ("experiments", re.compile(r"^experiments?[_\-.]", re.I)),
    ("prereg", re.compile(r"prereg|pre-reg|criterion|criteria", re.I)),
    ("limitations", re.compile(r"^limitations?[_\-.]", re.I)),
    ("lab log", re.compile(r"lab[_\-]?log|session[_\-]?handoff|handoff|pipeline[_\-]?notes", re.I)),
    ("paper draft", re.compile(r"^paper[_\-]|^draft|^manuscript|^narrative|^venues?[_\-.]|^fixlist|^todo", re.I)),
    ("numbers", re.compile(r"^numbers?\.tex$", re.I)),
    ("bibliography", re.compile(r"\.bib$", re.I)),
]
PLACEHOLDER_STEMS = {"file", "filename", "name", "example", "foo", "bar", "x", "path",
                     "output", "input", "your", "my", "some", "test", "out"}
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(
    r"(?<![\w./<>{}$%*~\@:-])([A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:"
    + "|".join(sorted(MENTION_EXTS))
    + r"))(?![\w<>{}*$])",
    re.I,
)
BOT_RE = re.compile(r"bot\b|\[bot\]|claude|copilot|github-actions|dependabot|noreply\.anthropic", re.I)


def set_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def warn(msg):
    print("WARN: " + msg, file=sys.stderr)


def fmt_date(ts):
    try:
        return dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except (OSError, ValueError, OverflowError):
        return "?"


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        n /= 1024.0
    return "%d B" % n


def mask_url_credentials(text):
    return re.sub(r"//[^/@\s]+@", "//***@", text)


# ---------------------------------------------------------------- walking

def walk_project(root):
    """Return (files, skipped_dirs). files: list of dicts with rel, size, mtime."""
    files, skipped = [], set()
    for dirpath, dirnames, filenames in os.walk(root):
        keep = []
        for d in dirnames:
            if d in PRUNE_DIRS or d.startswith("."):
                skipped.add(d)
            else:
                keep.append(d)
        dirnames[:] = sorted(keep)
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace("\\", "/")
            files.append({"rel": rel, "size": st.st_size, "mtime": st.st_mtime})
            if len(files) >= MAX_FILES:
                warn("stopped after %d files; the inventory is partial" % MAX_FILES)
                return files, skipped
    return files, skipped


def build_tree(files, depth, max_files_per_dir=12):
    """Return text lines for a tree limited to `depth` directory levels."""
    tree = {"dirs": {}, "files": []}
    for f in files:
        parts = f["rel"].split("/")
        node = tree
        for p in parts[:-1]:
            node = node["dirs"].setdefault(p, {"dirs": {}, "files": []})
        node["files"].append(parts[-1])

    def count(node):
        return len(node["files"]) + sum(count(c) for c in node["dirs"].values())

    lines = []

    def emit(node, level, prefix):
        for name in sorted(node["dirs"]):
            child = node["dirs"][name]
            lines.append("%s%s/  (%d files in total)" % (prefix, name, count(child)))
            if level < depth:
                emit(child, level + 1, prefix + "  ")
        shown = sorted(node["files"])
        for fn in shown[:max_files_per_dir]:
            lines.append("%s%s" % (prefix, fn))
        if len(shown) > max_files_per_dir:
            lines.append("%s... +%d more files" % (prefix, len(shown) - max_files_per_dir))

    emit(tree, 1, "")
    return lines


# ---------------------------------------------------------------- git

def run_git(root, args):
    try:
        p = subprocess.run(
            ["git", "-c", "core.quotepath=false", "-C", root] + args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    out = p.stdout.decode("utf-8", "replace")
    if p.returncode != 0:
        return False, p.stderr.decode("utf-8", "replace").strip()
    return True, out


def merge_identities(commits):
    """Group git identities that are probably one person (same email, same
    name, or one normalised name being a prefix of another)."""
    idents = {}
    for c in commits:
        key = (c["author"].strip(), c["email"].strip().lower())
        e = idents.setdefault(key, {"count": 0, "first": c["date"], "last": c["date"]})
        e["count"] += 1
        e["last"] = c["date"]
    keys = list(idents)
    parent = list(range(len(keys)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def norm(name):
        return re.sub(r"[^a-z]", "", name.lower())

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            (n1, e1), (n2, e2) = keys[i], keys[j]
            m1, m2 = norm(n1), norm(n2)
            same = (e1 == e2 and e1) or n1.lower() == n2.lower()
            prefix = min(len(m1), len(m2)) >= 5 and (m1.startswith(m2) or m2.startswith(m1))
            if same or prefix:
                parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i, k in enumerate(keys):
        groups[find(i)].append(k)
    authors = []
    for members in groups.values():
        names = sorted({m[0] for m in members}, key=lambda n: -sum(idents[m]["count"] for m in members if m[0] == n))
        emails = sorted({m[1] for m in members})
        placeholder = any(re.search(r"example\.(com|org)$|^your[_-]", m[1] + " " + m[0], re.I) for m in members)
        authors.append({
            "name": names[0],
            "aliases": names[1:],
            "commits": sum(idents[m]["count"] for m in members),
            "emails": emails,
            "first": min(idents[m]["first"] for m in members),
            "last": max(idents[m]["last"] for m in members),
            "looks_like_bot": bool(BOT_RE.search(" ".join(names) + " " + " ".join(emails))),
            "placeholder_identity": placeholder,
        })
    authors.sort(key=lambda a: -a["commits"])
    return authors


def git_summary(root):
    info = {"is_repo": False}
    ok, out = run_git(root, ["rev-parse", "--show-toplevel"])
    if not ok:
        first = out.splitlines()[0] if out else "git unavailable"
        warn("not a git repository or git unavailable (%s)" % first)
        return info
    info["is_repo"] = True
    info["toplevel"] = out.strip().replace("\\", "/")
    ok, out = run_git(root, ["log", "--reverse", "--format=%x1e%h%x1f%aN%x1f%aE%x1f%aI%x1f%s%x1f%b"])
    commits = []
    if ok:
        for rec in out.split("\x1e"):
            if not rec.strip():
                continue
            parts = rec.split("\x1f")
            if len(parts) < 5:
                continue
            commits.append({
                "hash": parts[0].strip(), "author": parts[1], "email": parts[2],
                "date": parts[3][:10], "subject": parts[4],
                "body": parts[5] if len(parts) > 5 else "",
            })
    else:
        warn("git log failed: %s" % out)
    info["commit_count"] = len(commits)
    info["first_date"] = commits[0]["date"] if commits else None
    info["last_date"] = commits[-1]["date"] if commits else None
    agent_assisted = sum(
        1 for c in commits
        if re.search(r"co-authored-by:.*(claude|anthropic|copilot|codex)", c["body"], re.I))
    info["authors"] = merge_identities(commits)
    info["agent_coauthored_commits"] = agent_assisted
    info["commits"] = commits
    ok, out = run_git(root, ["branch", "-a", "--format=%(refname:short)"])
    info["branches"] = [b.strip() for b in out.splitlines() if b.strip()] if ok else []
    ok, out = run_git(root, ["remote", "-v"])
    info["remotes"] = sorted({re.sub(r"\s+\((fetch|push)\)$", "", mask_url_credentials(l.strip())).replace(chr(9), " ")
                              for l in out.splitlines() if l.strip()}) if ok else []
    ok, out = run_git(root, ["rev-list", "--all", "--count"])
    info["commit_count_all_branches"] = int(out.strip()) if ok and out.strip().isdigit() else None
    ok, out = run_git(root, ["status", "--porcelain=v1"])
    untracked, modified = [], []
    if ok:
        for line in out.splitlines():
            if line.startswith("??"):
                untracked.append(line[3:].strip().strip('"'))
            elif line.strip():
                modified.append(line.strip())
    info["untracked"] = untracked
    info["modified"] = modified
    return info


# ---------------------------------------------------------------- analysis

def read_text(root, rel):
    try:
        full = os.path.join(root, rel)
        if os.path.getsize(full) > MAX_TEXT_BYTES:
            return None
        with open(full, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def first_heading(text):
    for line in text.splitlines()[:40]:
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()[:90]
    return ""


def key_documents(root, files):
    found = []
    seen = set()
    for f in files:
        rel = f["rel"]
        parts = rel.split("/")
        base = parts[-1]
        if len(parts) > 4:
            continue
        if ".provenance." in base.lower() or base.lower().endswith("provenance.json"):
            continue
        ext = os.path.splitext(base)[1].lower()
        kinds = []
        for kind, pat in KEY_DOC_PATTERNS:
            if pat.search(base) and (kind == "bibliography" or ext in (".md", ".tex", ".txt", ".json", ".rst", ".bib", "")):
                kinds.append(kind)
        if "prereg" in [p.lower() for p in parts[:-1]]:
            kinds.append("prereg")
        if parts[0].lower() == "claims" and ext == ".json":
            kinds.append("claims")
        if ext == ".tex" and len(parts) > 1 and parts[0].lower() in ("paper", "manuscript", "draft", "tex"):
            kinds.append("paper source")
        if kinds and rel not in seen:
            seen.add(rel)
            heading = ""
            if ext in (".md", ".txt", ".tex", ".rst"):
                t = read_text(root, rel)
                heading = first_heading(t) if t else ""
            found.append({"path": rel, "kinds": sorted(set(kinds)), "size": f["size"],
                          "modified": fmt_date(f["mtime"]), "heading": heading})
    return sorted(found, key=lambda d: (len(d["path"].split("/")), d["path"]))


def results_inventory(files):
    """Directories named results* at depth 1 or 2, with their immediate children."""
    roots = set()
    for f in files:
        parts = f["rel"].split("/")
        for i in range(min(2, len(parts) - 1)):
            if parts[i].lower().startswith("result"):
                roots.add("/".join(parts[: i + 1]))
    out = []
    for r in sorted(roots):
        prefix = r + "/"
        children = defaultdict(lambda: {"files": 0, "size": 0, "newest": 0.0})
        direct = {"files": 0, "size": 0, "newest": 0.0}
        for f in files:
            if not f["rel"].startswith(prefix):
                continue
            rest = f["rel"][len(prefix):].split("/")
            target = children[rest[0]] if len(rest) > 1 else direct
            target["files"] += 1
            target["size"] += f["size"]
            target["newest"] = max(target["newest"], f["mtime"])
        out.append({
            "root": r,
            "direct_files": direct["files"],
            "direct_newest": fmt_date(direct["newest"]) if direct["files"] else "",
            "subdirs": [
                {"path": r + "/" + name, "name": name, "files": v["files"], "size": v["size"],
                 "newest": fmt_date(v["newest"])}
                for name, v in sorted(children.items())
            ],
        })
    return out


def provenance_info(files):
    sidecars = [f for f in files if "provenance" in f["rel"].lower().split("/")[-1]]
    by_dir = Counter("/".join(f["rel"].split("/")[:-1]) or "." for f in sidecars)
    return {"count": len(sidecars), "by_dir": dict(by_dir.most_common(8)),
            "examples": [f["rel"] for f in sidecars[:5]]}


def load_texts(root, files, exclude):
    texts = {}
    for f in files:
        ext = os.path.splitext(f["rel"])[1].lower()
        if ext in TEXT_EXTS and f["rel"] not in exclude and os.path.basename(f["rel"]) != "PROJECT_INVENTORY.md":
            t = read_text(root, f["rel"])
            if t is not None:
                texts[f["rel"]] = t
    return texts


def orphan_results(results, texts):
    blob = "\n".join(texts.values())
    orphans = []
    for r in results:
        cands = list(r["subdirs"])
        if not cands and r["direct_files"]:
            cands = [{"path": r["root"], "name": r["root"].split("/")[-1], "files": r["direct_files"]}]
        for d in cands:
            path, name = d["path"], d["name"]
            mentioned = path in blob
            if not mentioned and len(name) >= 4:
                mentioned = re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", blob) is not None
            if not mentioned:
                orphans.append({"path": path, "files": d["files"]})
    return orphans


def missing_documents(texts, files, commits):
    all_paths = {f["rel"].lower() for f in files}
    basenames = {p.split("/")[-1] for p in all_paths}
    refs = defaultdict(list)

    def scan(source, text):
        text = URL_RE.sub(" ", text)
        for ln, line in enumerate(text.splitlines(), 1):
            for m in MENTION_RE.finditer(line):
                tok = m.group(1).strip(".")
                if len(tok) < 4 or ".." in tok:
                    continue
                stem = os.path.splitext(tok.split("/")[-1])[0].lower()
                if stem in PLACEHOLDER_STEMS or re.search(r"yyyy|xxx", tok, re.I):
                    continue
                refs[tok].append("%s:%d" % (source, ln))

    for rel, t in texts.items():
        scan(rel, t)
    for c in commits:
        scan("commit " + c["hash"], c["subject"] + "\n" + c["body"])

    missing = []
    for tok, where in refs.items():
        low = tok.lower().lstrip("./")
        base = low.split("/")[-1]
        if low in all_paths or base in basenames:
            continue
        ok = False
        for src in where:
            sp = src.split(":")[0]
            if sp.startswith("commit "):
                continue
            d = os.path.dirname(sp).lower()
            while True:
                cand = (d + "/" + low) if d else low
                if cand in all_paths:
                    ok = True
                    break
                if not d:
                    break
                d = os.path.dirname(d)
            if ok:
                break
        if ok:
            continue
        ext = os.path.splitext(tok)[1].lstrip(".").lower()
        missing.append({"name": tok, "kind": "document" if ext in DOC_EXTS else "data or code",
                        "mentions": len(where), "first_seen": where[0]})
    missing.sort(key=lambda m: (m["kind"] != "document", -m["mentions"], m["name"]))
    return missing


# ---------------------------------------------------------------- report

def commit_days(commits):
    days = defaultdict(list)
    for c in commits:
        days[c["date"]].append(c)
    return [(d, days[d]) for d in sorted(days)]


def render(data, args):
    L = []
    a = L.append
    a("# Project inventory: %s" % data["project_name"])
    a("")
    a("Generated %s by inventory_project.py. Everything below is read from disk and git; nothing is interpreted." % data["generated"])
    a("")
    a("## Summary")
    a("")
    g = data["git"]
    a("- Files scanned: %d (skipped dirs: %s)" % (data["file_count"], ", ".join(sorted(data["skipped_dirs"])) or "none"))
    if g.get("is_repo"):
        a("- Git: %d commits, %s to %s, %d human author(s) after merging identities, %d untracked paths, %d modified"
          % (g["commit_count"], g["first_date"], g["last_date"],
             len([x for x in g["authors"] if not x["placeholder_identity"] and not x["looks_like_bot"]]),
             len(g["untracked"]), len(g["modified"])))
    else:
        a("- Git: not a repository (or git unavailable)")
    a("- Results folders: %d, provenance sidecars: %d" % (sum(len(r["subdirs"]) or 1 for r in data["results"]), data["provenance"]["count"]))
    a("- Key documents found: %d, results folders no document mentions: %d, documents mentioned but absent: %d"
      % (len(data["key_documents"]), len(data["orphans"]), len([m for m in data["missing"] if m["kind"] == "document"])))
    a("")
    a("## Git")
    a("")
    if g.get("is_repo"):
        if g["toplevel"].rstrip("/").lower() != data["project_dir"].rstrip("/").lower():
            a("Note: the repository root is %s, a parent of the inspected folder." % g["toplevel"])
            a("")
        a("- Commits on the current branch: %d (all branches: %s)" % (g["commit_count"], g.get("commit_count_all_branches")))
        a("- First commit: %s; last commit: %s" % (g["first_date"], g["last_date"]))
        a("- Commits with an AI-assistant co-author trailer: %d" % g["agent_coauthored_commits"])
        a("- Branches: %s" % (", ".join(g["branches"]) or "none"))
        a("- Remotes: %s" % ("; ".join(g["remotes"]) or "none"))
        a("")
        a("Git identities that share an email, a name or a name prefix are merged into one author row.")
        a("")
        a("| Author | Commits | First | Last | Other names used | Emails | Note |")
        a("|---|---|---|---|---|---|---|")
        for au in g["authors"]:
            note = []
            if au["looks_like_bot"]:
                note.append("looks like a bot or agent")
            if au["placeholder_identity"]:
                note.append("placeholder git identity (unset user.name or user.email)")
            a("| %s | %d | %s | %s | %s | %s | %s |" % (
                au["name"], au["commits"], au["first"], au["last"], ", ".join(au["aliases"]),
                ", ".join(au["emails"]), "; ".join(note)))
        a("")
        a("### Commits by date" + (" (all commits)" if args.all_commits else ""))
        a("")
        if args.all_commits:
            for c in g["commits"]:
                a("- %s %s %s: %s" % (c["date"], c["hash"], c["author"], c["subject"]))
        else:
            a("| Date | Commits | Subjects (first three) |")
            a("|---|---|---|")
            for d, cs in commit_days(g["commits"]):
                subj = "; ".join(c["subject"][:70] for c in cs[:3]).replace("|", "/")
                a("| %s | %d | %s |" % (d, len(cs), subj))
            a("")
            a("Use --all-commits for every commit line.")
        a("")
        a("### Untracked paths (%d)" % len(g["untracked"]))
        a("")
        for u in g["untracked"][:80]:
            a("- %s" % u)
        if len(g["untracked"]) > 80:
            a("- ... +%d more" % (len(g["untracked"]) - 80))
        if not g["untracked"]:
            a("- none")
        a("")
        if g["modified"]:
            a("### Modified or staged paths (%d)" % len(g["modified"]))
            a("")
            for u in g["modified"][:40]:
                a("- %s" % u)
            a("")
    else:
        a("No git history available.")
        a("")
    a("## Key documents")
    a("")
    if data["key_documents"]:
        a("| Path | Kind | Modified | Size | First heading |")
        a("|---|---|---|---|---|")
        for d in data["key_documents"][:70]:
            a("| %s | %s | %s | %s | %s |" % (d["path"], ", ".join(d["kinds"]), d["modified"],
                                               human_size(d["size"]), d["heading"].replace("|", "/")))
        if len(data["key_documents"]) > 70:
            a("")
            a("... +%d more" % (len(data["key_documents"]) - 70))
    else:
        a("None of the usual names (README, RESULTS, CLAIMS, PROJECT, EXPERIMENTS, PREREG, LIMITATIONS, LAB_LOG, numbers.tex, *.bib) were found.")
    a("")
    a("## Results inventory")
    a("")
    if data["results"]:
        for r in data["results"]:
            a("### %s/" % r["root"])
            a("")
            if r["direct_files"]:
                a("- files directly in this folder: %d (newest %s)" % (r["direct_files"], r["direct_newest"]))
                a("")
            if r["subdirs"]:
                a("| Folder | Files | Size | Newest file |")
                a("|---|---|---|---|")
                for s in r["subdirs"][:60]:
                    a("| %s | %d | %s | %s |" % (s["path"], s["files"], human_size(s["size"]), s["newest"]))
                if len(r["subdirs"]) > 60:
                    a("")
                    a("... +%d more folders" % (len(r["subdirs"]) - 60))
                a("")
    else:
        a("No folder named results* was found at depth 1 or 2.")
        a("")
    p = data["provenance"]
    a("## Provenance sidecars")
    a("")
    a("- Files with 'provenance' in the name: %d" % p["count"])
    for d, n in p["by_dir"].items():
        a("- %s: %d" % (d, n))
    a("")
    a("## Results folders that no .md or .tex file mentions")
    a("")
    if data["orphans"]:
        a("A folder is listed when neither its path nor (for names of 4+ characters) its bare name appears in any scanned text file.")
        a("")
        for o in data["orphans"][:60]:
            a("- %s (%d files)" % (o["path"], o["files"]))
    else:
        a("None.")
    a("")
    a("## Documents mentioned but absent on disk")
    a("")
    a("A name is listed when no file with that path or base name exists anywhere in the scanned tree. It may be a generated, ignored, renamed or planned file.")
    a("")
    docs = [m for m in data["missing"] if m["kind"] == "document"]
    other = [m for m in data["missing"] if m["kind"] != "document"]
    for title, items, cap in (("Documents", docs, 60), ("Data or code files", other, 40)):
        a("### %s (%d)" % (title, len(items)))
        a("")
        if not items:
            a("- none")
        for m in items[:cap]:
            a("- %s (%d mention%s, first at %s)" % (m["name"], m["mentions"], "" if m["mentions"] == 1 else "s", m["first_seen"]))
        if len(items) > cap:
            a("- ... +%d more (see --json)" % (len(items) - cap))
        a("")
    a("## File tree (depth %d)" % args.depth)
    a("")
    a("```")
    L.extend(data["tree"])
    a("```")
    a("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Inventory a research project: file tree, git history summary, results folders, "
                    "key documents, orphan results and documents mentioned but absent.")
    ap.add_argument("project_dir", help="project root to inspect (read only)")
    ap.add_argument("--out", default="paper/PROJECT_INVENTORY.md",
                    help="report path; relative paths are resolved against the project dir; "
                         "use '-' to print the report to stdout instead (default: %(default)s)")
    ap.add_argument("--all-commits", action="store_true", help="list every commit instead of a per-day table")
    ap.add_argument("--depth", type=int, default=3, help="file tree depth (default 3)")
    ap.add_argument("--json", action="store_true", help="print the collected data as JSON on stdout")
    args = ap.parse_args(argv)
    set_utf8_output()

    root = os.path.abspath(args.project_dir)
    if not os.path.isdir(root):
        print("ERROR: not a directory: %s" % args.project_dir, file=sys.stderr)
        return 2
    root = root.replace("\\", "/")

    out_path = None
    if args.out != "-":
        out_path = args.out if os.path.isabs(args.out) else os.path.join(root, args.out)
        out_path = out_path.replace("\\", "/")

    files, skipped = walk_project(root)
    exclude = set()
    if out_path and out_path.startswith(root + "/"):
        exclude.add(out_path[len(root) + 1:])
    git = git_summary(root)
    results = results_inventory(files)
    texts = load_texts(root, files, exclude)
    commits = git.get("commits", [])
    data = {
        "project_name": os.path.basename(root.rstrip("/")),
        "project_dir": root,
        "generated": dt.date.today().isoformat(),
        "file_count": len(files),
        "skipped_dirs": sorted(skipped),
        "git": git,
        "key_documents": key_documents(root, files),
        "results": results,
        "provenance": provenance_info(files),
        "orphans": orphan_results(results, texts),
        "missing": missing_documents(texts, files, commits),
        "tree": build_tree(files, args.depth),
    }
    report = render(data, args)

    wrote = False
    if out_path:
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(report)
            wrote = True
        except OSError as exc:
            warn("could not write %s (%s); printing the report instead" % (out_path, exc))

    if args.json:
        print(json.dumps(data, indent=2, default=list))
    elif not wrote:
        print(report)
    else:
        g = data["git"]
        print("Inventory written to %s" % out_path)
        print("files scanned: %d" % data["file_count"])
        if g.get("is_repo"):
            names = ", ".join("%s (%d)%s" % (au["name"], au["commits"], " [placeholder]" if au["placeholder_identity"] else "")
                              for au in g["authors"])
            print("git: %d commits, %s to %s" % (g["commit_count"], g["first_date"], g["last_date"]))
            print("authors: %s" % names)
            print("untracked paths: %d" % len(g["untracked"]))
        print("key documents: %d" % len(data["key_documents"]))
        print("results folders: %d, orphans: %d" % (sum(len(r["subdirs"]) or 1 for r in results), len(data["orphans"])))
        print("provenance sidecars: %d" % data["provenance"]["count"])
        print("missing documents: %d, missing data or code files: %d"
              % (len([m for m in data["missing"] if m["kind"] == "document"]),
                 len([m for m in data["missing"] if m["kind"] != "document"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
