#!/usr/bin/env python3
"""Maintainer self-check for the research-paper-pilot skill folder.

Not part of the research workflow. Run it before publishing a change.

Checks (each prints PASS, FAIL or WARN):
  1. SKILL.md exists and has frontmatter with name and description
  2. SKILL.md is at most 300 lines
  3. the description is at most 1000 characters
  4. the frontmatter name equals the folder name
  5. every file in references/, templates/, agents/ and scripts/ is mentioned in SKILL.md
  6. every references/, templates/, agents/ or scripts/ path in SKILL.md resolves to a file
  7. the same paths mentioned in other markdown files resolve (WARN only, because a
     research project can have its own scripts/ folder)
  8. every script answers --help
  9. markdown files stay under 400 lines and start with "## Contents" above 100 lines
 10. no em dashes anywhere in the skill
 11. no machine-specific absolute paths in the skill
 12. every scripts/<name>.py named in SKILL.md, references/, templates/ or agents/ exists (WARN only)
 13. the version in SKILL.md metadata.version matches ../../.claude-plugin/plugin.json and
     marketplace.json when those manifests exist (WARN only; skipped when the skill is installed alone)

Links and paths are read outside fenced code blocks; markdown links also outside inline code.

Exit code is 1 when any check FAILs, otherwise 0. Stdlib only.
"""
import argparse
import json
import os
import re
import subprocess
import sys

SUBDIRS = ("references", "templates", "agents", "scripts")
EM_DASH = chr(0x2014)
PATH_RE = re.compile(r"(?<![\w/.-])((?:references|templates|agents|scripts)/[A-Za-z0-9_./\-]*[A-Za-z0-9_])(?![A-Za-z0-9_]*[<*{$\[])")
SCRIPT_MENTION_RE = re.compile(r"(?<![\w/.-])scripts/([A-Za-z0-9_\-]+\.py)(?![\w-])")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
MACHINE_PATH_RE = re.compile(r"[A-Za-z]:[/\\]+(?:Users|Documents and Settings)\b|(?<![\w.])/(?:home|Users)/[A-Za-z0-9_.-]+/")


class Report:
    def __init__(self):
        self.fails = 0
        self.warns = 0

    def line(self, status, name, detail=""):
        if status == "FAIL":
            self.fails += 1
        elif status == "WARN":
            self.warns += 1
        print("%s  %s%s" % (status, name, (": " + detail) if detail else ""))


def parse_frontmatter(text):
    """Return (dict, error). Handles plain, quoted and block-scalar values."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "file does not start with ---"
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, "frontmatter is not closed"
    fm = {}
    i = 1
    while i < end:
        m = re.match(r"^([A-Za-z0-9_\-]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).rstrip()
        if val in (">", "|", ">-", "|-", ">+", "|+"):
            folded = val.startswith(">")
            parts = []
            i += 1
            while i < end and (lines[i].startswith(" ") or not lines[i].strip()):
                parts.append(lines[i].strip())
                i += 1
            fm[key] = (" " if folded else "\n").join(p for p in parts if p or not folded).strip()
            continue
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
            if lines[i].lstrip().startswith(key + ': "'):
                val = val.replace('\\"', '"')
        else:
            # plain scalar continued on indented lines
            j = i + 1
            while j < end and lines[j].startswith(" ") and not re.match(r"^\s+[A-Za-z0-9_\-]+:\s", lines[j]):
                val += " " + lines[j].strip()
                j += 1
            i = j - 1
        fm[key] = val
        i += 1
    return fm, None


def list_files(skill_dir, sub):
    base = os.path.join(skill_dir, sub)
    out = []
    if os.path.isdir(base):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != "__pycache__" and not d.startswith(".")]
            for fn in filenames:
                if fn.endswith((".pyc", ".pyo")) or fn.startswith("."):
                    continue
                out.append(os.path.relpath(os.path.join(dirpath, fn), skill_dir).replace("\\", "/"))
    return sorted(out)


def read(path):
    # utf-8-sig: a byte-order mark some editors add must not hide the opening ---
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def strip_code(text, inline=True):
    """Blank fenced code blocks (and, with inline=True, `inline code` spans); line count is kept."""
    out, fence = [], None
    for line in text.split("\n"):
        m = FENCE_RE.match(line)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            out.append("")
            continue
        if m:
            fence = m.group(1)
            out.append("")
            continue
        if inline:
            line = re.sub(r"(`+).+?\1", lambda c: " " * len(c.group(0)), line)
        out.append(line)
    return "\n".join(out)


def mentioned(path, text):
    """True if the relative path or its basename appears as a whole token (gate.py is not prose_gate.py)."""
    for t in (path, os.path.basename(path)):
        if re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", text):
            return True
    return False


def nested_value(text, parent, key):
    """Value of `parent: / key: value` in YAML frontmatter text (one nesting level), or None."""
    m = re.search(r"^" + re.escape(parent) + r":[ \t]*\n((?:[ \t]+.*(?:\n|$)|[ \t]*\n)*)", text, re.M)
    if not m:
        return None
    v = re.search(r"^[ \t]+" + re.escape(key) + r":[ \t]*[\"']?([^\"'\s#]+)", m.group(1), re.M)
    return v.group(1) if v else None


def version_check(skill_dir, text, name):
    """(status, detail) comparing SKILL.md metadata.version with the plugin manifests, or None when the
    manifests are absent (the skill can be installed on its own)."""
    plug_dir = os.path.normpath(os.path.join(skill_dir, "..", "..", ".claude-plugin"))
    found = []
    m = re.match(r"^---[ \t]*\n(.*?)\n---", text, re.S)
    skill_v = nested_value(m.group(1), "metadata", "version") if m else None
    problems = []
    for fn in ("plugin.json", "marketplace.json"):
        path = os.path.join(plug_dir, fn)
        if not os.path.isfile(path):
            continue
        try:
            data = json.loads(read(path))
        except ValueError as exc:
            problems.append("%s does not parse (%s)" % (fn, exc))
            continue
        if not isinstance(data, dict):
            continue
        if fn == "plugin.json":
            found.append(("plugin.json version", data.get("version")))
        else:
            meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            if "version" in meta:
                found.append(("marketplace.json metadata.version", meta.get("version")))
            plugins = [x for x in data.get("plugins") or [] if isinstance(x, dict)]
            own = [x for x in plugins if x.get("name") == name] or plugins
            for x in own:
                if "version" in x:
                    found.append(("marketplace.json plugins[%s].version" % x.get("name", "?"), x.get("version")))
    if not found and not problems:
        return None
    found.insert(0, ("SKILL.md metadata.version", skill_v))
    versions = {str(v) for _, v in found}
    detail = ", ".join("%s=%s" % (k, v) for k, v in found)
    if problems or len(versions) > 1 or skill_v is None:
        return "WARN", "; ".join(problems + [detail])
    return "PASS", detail


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(
        description="Maintainer self-check for a skill folder: SKILL.md size and description length, "
                    "file coverage and link resolution, --help on every script, style limits. "
                    "Prints PASS/FAIL per check; exit code 1 if any check fails.")
    ap.add_argument("skill_dir", nargs="?", default=os.path.dirname(here),
                    help="skill folder that holds SKILL.md (default: the folder above this script)")
    ap.add_argument("--max-lines", type=int, default=300, help="SKILL.md line limit (default 300)")
    ap.add_argument("--max-description", type=int, default=1000, help="description character limit (default 1000)")
    ap.add_argument("--forbid", action="append", default=[],
                    help="extra word that must not appear anywhere in the skill (repeatable, case-insensitive)")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    skill_dir = os.path.abspath(args.skill_dir)
    rep = Report()
    print("Checking %s" % skill_dir.replace("\\", "/"))
    print("")

    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        rep.line("FAIL", "SKILL.md exists", "not found")
        print("")
        print("1 check failed; nothing else can be checked without SKILL.md")
        return 1
    text = read(skill_md)
    rep.line("PASS", "SKILL.md exists")

    fm, err = parse_frontmatter(text)
    if fm is None or not fm.get("name") or not fm.get("description"):
        rep.line("FAIL", "frontmatter has name and description", err or "name or description missing")
        fm = fm or {}
    else:
        rep.line("PASS", "frontmatter has name and description")

    n_lines = len(text.splitlines())
    rep.line("PASS" if n_lines <= args.max_lines else "FAIL", "SKILL.md line count",
             "%d lines (limit %d)" % (n_lines, args.max_lines))

    desc = fm.get("description", "")
    rep.line("PASS" if 0 < len(desc) <= args.max_description else "FAIL", "description length",
             "%d characters (limit %d)" % (len(desc), args.max_description))

    name = fm.get("name", "")
    folder = os.path.basename(skill_dir.rstrip("/\\"))
    rep.line("PASS" if name == folder else "FAIL", "frontmatter name equals folder name",
             "name=%r folder=%r" % (name, folder))

    # coverage: every file mentioned at least once
    all_files = []
    for sub in SUBDIRS:
        all_files.extend(list_files(skill_dir, sub))
    unmentioned = [f for f in all_files if not mentioned(f, text)]
    if not all_files:
        rep.line("FAIL", "every file in references/, templates/, agents/, scripts/ is mentioned in SKILL.md",
                 "no files found in those folders")
    else:
        rep.line("PASS" if not unmentioned else "FAIL",
                 "every file in references/, templates/, agents/, scripts/ is mentioned in SKILL.md",
                 "%d files, %d not mentioned%s" % (len(all_files), len(unmentioned),
                                                   (": " + ", ".join(unmentioned[:8])) if unmentioned else ""))

    # resolution in SKILL.md
    def unresolved_in(content, base_dir):
        bad = []
        for m in PATH_RE.finditer(strip_code(content, inline=False)):
            rel = m.group(1)
            if "/" not in rel.rstrip("/"):
                continue
            if not os.path.exists(os.path.join(base_dir, rel)):
                bad.append(rel)
        for m in re.finditer(r"\]\(([^)#\s]+)\)", strip_code(content)):
            target = m.group(1)
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            if not os.path.exists(os.path.join(base_dir, target)):
                bad.append(target)
        return sorted(set(bad))

    bad = unresolved_in(text, skill_dir)
    rep.line("PASS" if not bad else "FAIL", "every path mentioned in SKILL.md resolves",
             "%d unresolved%s" % (len(bad), (": " + ", ".join(bad[:8])) if bad else ""))

    # resolution in the other markdown files
    other_bad = {}
    for f in all_files:
        if f.endswith(".md"):
            b = unresolved_in(read(os.path.join(skill_dir, f)), skill_dir)
            if b:
                other_bad[f] = b
    if other_bad:
        detail = "; ".join("%s -> %s" % (f, ", ".join(b[:3])) for f, b in list(other_bad.items())[:5])
        rep.line("WARN", "paths mentioned in other markdown files resolve", detail)
    else:
        rep.line("PASS", "paths mentioned in other markdown files resolve")

    # --help on every script
    scripts = [f for f in all_files if f.startswith("scripts/") and f.endswith(".py")]
    help_bad = []
    for s in scripts:
        try:
            p = subprocess.run([sys.executable, os.path.join(skill_dir, s), "--help"],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            out = (p.stdout + p.stderr).decode("utf-8", "replace").lower()
            if p.returncode != 0 or "usage" not in out:
                help_bad.append("%s (exit %d)" % (s, p.returncode))
        except (OSError, subprocess.SubprocessError) as exc:
            help_bad.append("%s (%s)" % (s, exc))
    rep.line("PASS" if scripts and not help_bad else "FAIL", "every script answers --help",
             "%d scripts%s" % (len(scripts), (", failing: " + ", ".join(help_bad)) if help_bad else ""))

    # style limits
    md_files = ["SKILL.md"] + [f for f in all_files if f.endswith(".md")]
    long_files, contents_missing = [], []
    for f in md_files:
        t = read(os.path.join(skill_dir, f))
        n = len(t.splitlines())
        if f != "SKILL.md" and n > 400:
            long_files.append("%s (%d)" % (f, n))
        if n > 100:
            head = "\n".join(t.splitlines()[:25])
            if not re.search(r"^##\s+Contents\b", head, re.M):
                contents_missing.append(f)
    rep.line("PASS" if not long_files and not contents_missing else "FAIL",
             "markdown files under 400 lines; files over 100 lines open with ## Contents",
             "; ".join(filter(None, [
                 ("too long: " + ", ".join(long_files)) if long_files else "",
                 ("no Contents list: " + ", ".join(contents_missing)) if contents_missing else ""])))

    # em dashes and machine paths and forbidden words
    text_files = ["SKILL.md"] + [f for f in all_files if f.endswith((".md", ".py", ".json", ".txt"))]
    dash_hits, path_hits, word_hits = [], [], []
    for f in text_files:
        t = read(os.path.join(skill_dir, f))
        if EM_DASH in t:
            dash_hits.append("%s (%d)" % (f, t.count(EM_DASH)))
        if MACHINE_PATH_RE.search(t):
            path_hits.append(f)
        for w in args.forbid:
            if w and re.search(re.escape(w), t, re.I):
                word_hits.append("%s:%s" % (f, w))
    rep.line("PASS" if not dash_hits else "FAIL", "no em dashes in the skill", ", ".join(dash_hits[:8]))
    rep.line("PASS" if not path_hits else "FAIL", "no machine-specific absolute paths in the skill", ", ".join(path_hits[:8]))

    # scripts named in the docs exist (WARN: a research project can have its own scripts/ folder)
    doc_files = ["SKILL.md"] + [f for f in all_files if f.endswith(".md") and f.split("/")[0] in
                                ("references", "templates", "agents")]
    missing_scripts = {}
    for f in doc_files:
        for m in SCRIPT_MENTION_RE.finditer(read(os.path.join(skill_dir, f))):
            if not os.path.isfile(os.path.join(skill_dir, "scripts", m.group(1))):
                missing_scripts.setdefault("scripts/" + m.group(1), []).append(f)
    rep.line("WARN" if missing_scripts else "PASS", "every scripts/<name>.py named in the docs exists",
             "; ".join("%s (in %s)" % (k, ", ".join(sorted(set(v))[:3])) for k, v in sorted(missing_scripts.items())[:8]))

    # version agrees with the plugin manifests two levels up, when they exist
    vc = version_check(skill_dir, text, name)
    if vc:
        rep.line(vc[0], "SKILL.md version matches the plugin manifests", vc[1])
    if args.forbid:
        rep.line("PASS" if not word_hits else "FAIL", "no forbidden words", ", ".join(word_hits[:8]))

    print("")
    print("%d failed, %d warnings" % (rep.fails, rep.warns))
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main())
