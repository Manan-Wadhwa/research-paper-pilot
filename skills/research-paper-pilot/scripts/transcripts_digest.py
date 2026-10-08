#!/usr/bin/env python3
"""Digest the Claude Code session transcripts that belong to a project.

Claude Code stores one JSONL file per session in a per-project folder under
~/.claude/projects. The folder name is the project path with every character
that is not a letter or digit replaced by a dash (for example a drive colon
and the path separators). This script finds that folder for a project path,
reads each session and writes a dated markdown digest: date range, the
user's prompts (shortened), files written or edited, and git commit messages
found in shell commands.

Stdlib only. Record shapes differ between versions, so every record is read
defensively and unreadable lines are skipped. Anything that looks like a
token, key or password is masked before it reaches the output.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
from collections import Counter, defaultdict

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-+/=]{16,}"),
]
KEYWORD_RE = re.compile(
    r"(?i)([A-Za-z0-9_\-]*(?:api[_\-]?key|apikey|secret|token|passwd|password|pwd|credential|auth)[A-Za-z0-9_\-]*"
    r"\s*[=:]\s*)(['\"]?)([^\s'\",;]{4,})"
)
URL_CRED_RE = re.compile(r"(//[^/@\s:]+:)[^/@\s]+@")
LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/_\-=.])[A-Za-z0-9+/=]{28,}(?![A-Za-z0-9+/_\-=.])")

NOISE_PREFIXES = ("<system-reminder", "<task-notification", "<local-command", "[Request interrupted",
                  "Caveat:", "<command-message", "<user-prompt-submit-hook")


def mask(text):
    """Mask anything that looks like a credential. Applied to every output string."""
    if not text:
        return text
    for pat in SECRET_PATTERNS:
        text = pat.sub("[MASKED]", text)
    text = URL_CRED_RE.sub(r"\1[MASKED]@", text)
    text = KEYWORD_RE.sub(lambda m: m.group(1) + m.group(2) + "[MASKED]", text)

    def long_token(m):
        tok = m.group(0)
        if "/" in tok and re.search(r"[A-Za-z]{3,}/", tok):
            return tok  # looks like a path
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", tok):
            return tok  # git or sha256 digest, not a secret
        has_digit = re.search(r"\d", tok) is not None
        mixed = re.search(r"[a-z]", tok) is not None and re.search(r"[A-Z]", tok) is not None
        if has_digit and (mixed or re.fullmatch(r"[0-9a-f]{32,}", tok)):
            return "[MASKED]"
        return tok

    return LONG_TOKEN_RE.sub(long_token, text)


def warn(msg):
    print("WARN: " + msg, file=sys.stderr)


def set_utf8_output():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


# ------------------------------------------------------ folder discovery

def encode_variants(path):
    """Folder-name candidates for a project path. Claude Code replaces each
    non-alphanumeric character with a dash; the simpler rule (colon and path
    separators only) is tried as well, and both drive-letter cases."""
    p = os.path.abspath(path).replace("\\", "/").rstrip("/")
    strict = p.replace(":", "-").replace("/", "-")
    loose = re.sub(r"[^A-Za-z0-9]", "-", p)
    out = []
    for base in (strict, loose):
        for variant in (base, base[:1].lower() + base[1:], base[:1].upper() + base[1:]):
            if variant not in out:
                out.append(variant)
    # lowercase the drive letter first, since that is the more common spelling for some versions
    out.sort(key=lambda v: 0 if v[:1].islower() else 1)
    return out


def find_project_folders(projects_dir, project_dir, include_sub):
    if not os.path.isdir(projects_dir):
        return None, []
    names = [n for n in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, n))]
    lower = {n.lower(): n for n in names}
    exact = None
    for cand in encode_variants(project_dir):
        if cand in names:
            exact = cand
            break
        if cand.lower() in lower:
            exact = lower[cand.lower()]
            break
    related = []
    if include_sub or exact is None:
        base = (exact or encode_variants(project_dir)[0]).lower() + "-"
        related = [n for n in names if n.lower().startswith(base) and n != exact]
    return exact, sorted(related)


# ------------------------------------------------------------- parsing

def user_text(message):
    """Return the human-typed text of a user message, or '' for tool results."""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def clean_prompt(text, limit):
    text = re.sub(r"<[^>\n]{1,200}>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def commit_messages(command):
    """Pull commit subjects out of a shell command that runs `git commit`."""
    msgs = []
    if "git" not in command or "commit" not in command:
        return msgs
    for m in re.finditer(r"git\b[^\n|;&]*\bcommit\b", command):
        tail = command[m.start():]
        heredoc = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)(?:\n\s*\1\b|\Z)", tail, re.S)
        if heredoc:
            first = next((l.strip() for l in heredoc.group(2).splitlines() if l.strip()), "")
            if first:
                msgs.append(first)
                continue
        here_ps = re.search(r"@['\"]\s*\n(.*?)\n['\"]@", tail, re.S)
        if here_ps:
            first = next((l.strip() for l in here_ps.group(1).splitlines() if l.strip()), "")
            if first:
                msgs.append(first)
                continue
        simple = re.search(r"(?:-m|--message)[ =]+(\"([^\"]*)\"|'([^']*)')", tail)
        if simple:
            msg = simple.group(2) if simple.group(2) is not None else simple.group(3)
            first = next((l.strip() for l in msg.splitlines() if l.strip()), "")
            if first and not first.startswith("$(cat"):
                msgs.append(first)
    return msgs


def parse_session(path):
    s = {
        "id": os.path.splitext(os.path.basename(path))[0],
        "file": path,
        "title": "",
        "first_ts": None,
        "last_ts": None,
        "branches": set(),
        "models": Counter(),
        "prompts": [],      # (timestamp, text)
        "writes": [],       # (timestamp, path, tool)
        "commits": [],      # (timestamp, message)
        "assistant_turns": 0,
        "bad_lines": 0,
    }
    seen_uuid = set()
    try:
        fh = open(path, "r", encoding="utf-8", errors="replace")
    except OSError as exc:
        warn("cannot open %s (%s)" % (path, exc))
        return s
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                s["bad_lines"] += 1
                continue
            if not isinstance(rec, dict):
                continue
            try:
                handle_record(s, rec, seen_uuid)
            except Exception:  # unknown record shape: skip it
                s["bad_lines"] += 1
    return s


def handle_record(s, rec, seen_uuid):
    typ = rec.get("type")
    ts = rec.get("timestamp") if isinstance(rec.get("timestamp"), str) else None
    if typ == "ai-title" and isinstance(rec.get("aiTitle"), str):
        s["title"] = rec["aiTitle"]
        return
    if ts:
        if s["first_ts"] is None or ts < s["first_ts"]:
            s["first_ts"] = ts
        if s["last_ts"] is None or ts > s["last_ts"]:
            s["last_ts"] = ts
    if isinstance(rec.get("gitBranch"), str) and rec["gitBranch"]:
        s["branches"].add(rec["gitBranch"])
    if rec.get("isSidechain"):
        return
    uid = rec.get("uuid")
    if uid:
        if uid in seen_uuid:
            return
        seen_uuid.add(uid)
    msg = rec.get("message")
    if typ == "user":
        if rec.get("isMeta"):
            return
        text = user_text(msg).strip()
        if not text or text.startswith(NOISE_PREFIXES):
            return
        s["prompts"].append((ts, text))
    elif typ == "assistant":
        s["assistant_turns"] += 1
        if isinstance(msg, dict):
            if isinstance(msg.get("model"), str):
                s["models"][msg["model"]] += 1
            content = msg.get("content")
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    name = block.get("name")
                    inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                    if name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                        fp = inp.get("file_path") or inp.get("notebook_path")
                        if isinstance(fp, str):
                            s["writes"].append((ts, fp, name))
                    elif name in ("Bash", "PowerShell"):
                        cmd = inp.get("command")
                        if isinstance(cmd, str):
                            for m in commit_messages(cmd):
                                s["commits"].append((ts, m))


# -------------------------------------------------------------- output

def day(ts):
    return ts[:10] if ts else "unknown"


def hhmm(ts):
    return ts[11:16] if ts and len(ts) >= 16 else ""


def project_relative(fp, project_dir):
    p = fp.replace("\\", "/")
    root = os.path.abspath(project_dir).replace("\\", "/").rstrip("/")
    if p.lower().startswith(root.lower() + "/"):
        return p[len(root) + 1:]
    return p


def build_digest(sessions, project_dir, args):
    L = []
    a = L.append
    a("# Transcript digest: %s" % mask(os.path.basename(os.path.abspath(project_dir).rstrip("/\\"))))
    a("")
    a("Generated %s. Times are UTC as recorded in the transcripts. Prompts are shortened to %d characters; "
      "credential-like strings are masked." % (dt.date.today().isoformat(), args.prompt_chars))
    a("")
    total_prompts = sum(len(s["prompts"]) for s in sessions)
    a("## Summary")
    a("")
    a("- Sessions: %d" % len(sessions))
    dated = [s for s in sessions if s["first_ts"]]
    if dated:
        a("- Date range: %s to %s" % (day(min(s["first_ts"] for s in dated)), day(max(s["last_ts"] for s in dated))))
    a("- User prompts: %d, files written or edited: %d, commit messages found: %d"
      % (total_prompts, len({w[1] for s in sessions for w in s["writes"]}), sum(len(s["commits"]) for s in sessions)))
    a("")
    a("## Timeline by day")
    a("")
    per_day = defaultdict(lambda: {"sessions": set(), "prompts": 0, "writes": 0, "commits": 0})
    for s in sessions:
        for ts, _ in s["prompts"]:
            d = per_day[day(ts)]
            d["sessions"].add(s["id"][:8])
            d["prompts"] += 1
        for ts, _, _ in s["writes"]:
            per_day[day(ts)]["writes"] += 1
        for ts, _ in s["commits"]:
            per_day[day(ts)]["commits"] += 1
    if per_day:
        a("| Day | Sessions | Prompts | File writes | Commits |")
        a("|---|---|---|---|---|")
        for d in sorted(per_day):
            v = per_day[d]
            a("| %s | %s | %d | %d | %d |" % (d, ", ".join(sorted(v["sessions"])) or "-", v["prompts"], v["writes"], v["commits"]))
    else:
        a("No dated activity found.")
    a("")
    for s in sessions:
        a("## Session %s" % s["id"][:8])
        a("")
        if s["title"]:
            a("- Title (auto-generated): %s" % mask(s["title"]))
        a("- Span: %s %s to %s %s" % (day(s["first_ts"]), hhmm(s["first_ts"]), day(s["last_ts"]), hhmm(s["last_ts"])))
        a("- Prompts: %d, assistant turns: %d%s" % (
            len(s["prompts"]), s["assistant_turns"],
            ", models: " + ", ".join(m for m, _ in s["models"].most_common(3)) if s["models"] else ""))
        if s["branches"]:
            a("- Git branches seen: %s" % mask(", ".join(sorted(s["branches"]))))
        a("")
        prompts = s["prompts"]
        a("### Prompts")
        a("")
        cap = args.max_prompts
        if len(prompts) > cap > 0:
            head, tail = prompts[: cap // 2], prompts[-(cap - cap // 2):]
            omitted = len(prompts) - cap
        else:
            head, tail, omitted = prompts, [], 0
        for ts, text in head:
            a("- %s %s  %s" % (day(ts), hhmm(ts), mask(clean_prompt(text, args.prompt_chars))))
        if omitted:
            a("- ... %d prompts omitted (raise --max-prompts to see them)" % omitted)
        for ts, text in tail:
            a("- %s %s  %s" % (day(ts), hhmm(ts), mask(clean_prompt(text, args.prompt_chars))))
        if not prompts:
            a("- none found")
        a("")
        a("### Files written or edited")
        a("")
        counts = Counter(project_relative(fp, project_dir) for _, fp, _ in s["writes"])
        for fp, n in counts.most_common(args.max_files):
            a("- %s%s" % (mask(fp), " (x%d)" % n if n > 1 else ""))
        if len(counts) > args.max_files:
            a("- ... +%d more files" % (len(counts) - args.max_files))
        if not counts:
            a("- none found")
        a("")
        a("### Git commit messages found in commands")
        a("")
        seen = set()
        for ts, m in s["commits"]:
            if m in seen:
                continue
            seen.add(m)
            a("- %s  %s" % (day(ts), mask(m[:160])))
        if not seen:
            a("- none found")
        a("")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Digest the Claude Code transcripts of a project: sessions, dated user prompts, "
                    "files written and commit messages. Credential-like strings are masked.")
    ap.add_argument("project_dir", help="the project path whose transcripts to read")
    ap.add_argument("--claude-projects-dir", default=os.path.join("~", ".claude", "projects"),
                    help="folder that holds the per-project transcript folders (default: ~/.claude/projects)")
    ap.add_argument("--out", default="paper/TRANSCRIPTS_DIGEST.md",
                    help="digest path; relative paths are resolved against the project dir; "
                         "'-' prints to stdout (default: %(default)s)")
    ap.add_argument("--include-parents", action="store_true",
                    help="when the project has no transcript folder, also read the nearest parent folder that has one "
                         "(sessions started from a parent directory, e.g. a workspace holding several projects)")
    ap.add_argument("--include-subprojects", action="store_true",
                    help="also read transcript folders of sub-folders of the project")
    ap.add_argument("--max-prompts", type=int, default=60,
                    help="prompts shown per session, first half and last half (0 = all; default 60)")
    ap.add_argument("--prompt-chars", type=int, default=200, help="characters kept per prompt (default 200)")
    ap.add_argument("--max-files", type=int, default=40, help="files listed per session (default 40)")
    ap.add_argument("--since", default="", help="only sessions that ended on or after this date (YYYY-MM-DD)")
    ap.add_argument("--json", action="store_true", help="print the digest data as JSON on stdout")
    args = ap.parse_args(argv)
    set_utf8_output()

    project_dir = os.path.abspath(args.project_dir)
    if not os.path.isdir(project_dir):
        warn("project dir does not exist on disk: %s (continuing; transcripts may still exist)" % args.project_dir)
    projects_dir = os.path.abspath(os.path.expanduser(args.claude_projects_dir))

    exact, related = find_project_folders(projects_dir, project_dir, args.include_subprojects)
    folders = ([exact] if exact else []) + (related if args.include_subprojects else [])
    if not os.path.isdir(projects_dir):
        warn("transcripts folder not found: %s" % projects_dir.replace("\\", "/"))
    elif not exact:
        parent_dir = os.path.dirname(project_dir)
        used_parent = False
        while parent_dir and parent_dir != os.path.dirname(parent_dir):
            pexact, _ = find_project_folders(projects_dir, parent_dir, False)
            if pexact:
                if args.include_parents:
                    folders = [pexact]
                    used_parent = True
                    warn("no folder for the project itself; reading the parent's sessions: %s (they may cover other projects)" % pexact)
                else:
                    warn("sessions were started from a parent folder (%s); add --include-parents to read them" % pexact)
                break
            parent_dir = os.path.dirname(parent_dir)
        if not used_parent:
            warn("no transcript folder for %s; tried: %s" % (project_dir.replace("\\", "/"), ", ".join(encode_variants(project_dir)[:3])))
    if related and not args.include_subprojects:
        warn("%d folder(s) of sub-projects exist; add --include-subprojects to read them: %s"
             % (len(related), ", ".join(related[:4])))

    sessions = []
    for folder in folders:
        fdir = os.path.join(projects_dir, folder)
        try:
            names = sorted(n for n in os.listdir(fdir) if n.endswith(".jsonl"))
        except OSError as exc:
            warn("cannot list %s (%s)" % (fdir, exc))
            continue
        for n in names:
            sessions.append(parse_session(os.path.join(fdir, n)))
    if args.since:
        sessions = [s for s in sessions if (s["last_ts"] or "")[:10] >= args.since]
    sessions = [s for s in sessions if s["first_ts"] or s["prompts"]]
    sessions.sort(key=lambda s: s["first_ts"] or "")

    digest = build_digest(sessions, project_dir, args)

    out_path = None
    if args.out != "-":
        base = project_dir if os.path.isdir(project_dir) else os.getcwd()
        out_path = args.out if os.path.isabs(args.out) else os.path.join(base, args.out)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(digest)
        except OSError as exc:
            warn("could not write %s (%s); printing the digest instead" % (out_path, exc))
            out_path = None

    if args.json:
        payload = {
            "project_dir": mask(project_dir.replace("\\", "/")),
            "folders": folders,
            "sessions": [{
                "id": s["id"], "title": mask(s["title"]), "first": s["first_ts"], "last": s["last_ts"],
                "prompts": [{"ts": ts, "text": mask(clean_prompt(t, args.prompt_chars))} for ts, t in s["prompts"]],
                "files_written": sorted({mask(w[1]) for w in s["writes"]}),
                "commits": [{"ts": ts, "message": mask(m)} for ts, m in s["commits"]],
            } for s in sessions],
        }
        print(json.dumps(payload, indent=2))
    elif out_path is None:
        print(digest)
    else:
        print("Digest written to %s" % out_path.replace("\\", "/"))
        print("transcript folder(s): %s" % (", ".join(folders) or "none found"))
        print("sessions: %d, prompts: %d, commit messages: %d"
              % (len(sessions), sum(len(s["prompts"]) for s in sessions), sum(len(s["commits"]) for s in sessions)))
        dated = [s for s in sessions if s["first_ts"]]
        if dated:
            print("date range: %s to %s" % (day(min(s["first_ts"] for s in dated)), day(max(s["last_ts"] for s in dated))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
