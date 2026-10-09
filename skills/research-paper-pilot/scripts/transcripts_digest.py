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
# key = value, key: value, "key": "value" and --key value. Only keys whose
# name looks like a credential are masked (see secret_key_name), so
# max_tokens, author or tokenizer are left alone.
KEYWORD_RE = re.compile(
    r"(?<![A-Za-z0-9_\-.])([A-Za-z][A-Za-z0-9_\-.]*['\"]?\s*[=:]\s*)(['\"]?)([^\s'\",;]{4,})"
)
FLAG_SECRET_RE = re.compile(r"(?<![\w-])(--?[A-Za-z][A-Za-z0-9_\-]*\s+)(['\"]?)([^\s'\",;\-][^\s'\",;]{3,})")
AUTH_HEADER_RE = re.compile(r"(?i)(\bauthorization['\"]?\s*[:=]\s*['\"]?(?:(?:basic|bearer|token|digest)\s+)?)([^\s'\",;]{4,})")
SECRET_LAST_PARTS = {"token", "secret", "password", "passwd", "passphrase", "apikey", "credential", "credentials",
                     "authorization", "bearer"}
SECRET_KEY_PREFIXES = {"api", "access", "secret", "private", "client", "auth", "signing", "encryption", "session"}
NOT_SECRET_VALUE_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?|\$\{?\w+\}?|<[^>]*>|\[MASKED\]|none|null|nil|true|false|basic|bearer|digest|x{3,}|\*+|\.{3,}|"
    r"(?:os\.)?(?:environ|getenv)\b.*|process\.env\b.*)$", re.I)
URL_CRED_RE = re.compile(r"(//[^/@\s:]+:)[^/@\s]+@")
LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9+/_\-=.])[A-Za-z0-9+/=]{28,}(?![A-Za-z0-9+/_\-=.])")

NOISE_PREFIXES = ("<system-reminder", "<task-notification", "<local-command", "[Request interrupted",
                  "Caveat:", "<command-message", "<command-name", "<command-args", "<command-stdout",
                  "<user-prompt-submit-hook", "<bash-input", "<bash-stdout", "<bash-stderr",
                  "This session is being continued from a previous conversation")
LEADING_REMINDERS_RE = re.compile(r"^(?:\s*<system-reminder>.*?</system-reminder>)+\s*", re.S)
SLASH_COMMAND_RE = re.compile(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>")


def mask(text):
    """Mask anything that looks like a credential. Applied to every output string."""
    if not text:
        return text
    for pat in SECRET_PATTERNS:
        text = pat.sub("[MASKED]", text)
    text = URL_CRED_RE.sub(r"\1[MASKED]@", text)
    text = AUTH_HEADER_RE.sub(lambda m: m.group(1) + "[MASKED]", text)

    def keyword(m):
        key = m.group(1).rstrip(" \t=:'\"")
        if secret_key_name(key) and not NOT_SECRET_VALUE_RE.match(m.group(3)):
            return m.group(1) + m.group(2) + "[MASKED]"
        return m.group(0)

    text = KEYWORD_RE.sub(keyword, text)
    text = FLAG_SECRET_RE.sub(keyword, text)

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


def secret_key_name(key):
    """True for key names that usually hold a credential: api_key, apiKey,
    secret, client_secret, password, db_passwd, token, access_token,
    authToken, Authorization. False for max_tokens, author, tokenizer, pwd."""
    key = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key.lstrip("-"))
    parts = [x for x in re.split(r"[_\-.]+", key.lower()) if x]
    if not parts:
        return False
    last = parts[-1]
    prev = parts[-2] if len(parts) > 1 else ""
    if last in SECRET_LAST_PARTS:
        return True
    if last == "key" and prev in SECRET_KEY_PREFIXES:
        return True
    if last in ("pwd", "pass", "auth") and prev:
        return True  # db_pwd, smtp_pass, basic_auth (but not a bare pwd or auth)
    return False


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
        bases = {v.lower() + "-" for v in encode_variants(project_dir)}
        if exact:
            bases.add(exact.lower() + "-")
        # The folder name is lossy (myproj-v2 also starts with myproj-), so
        # sessions read from these folders are checked against their recorded cwd.
        related = [n for n in names if n != exact and any(n.lower().startswith(b) for b in bases)]
    return exact, sorted(related)


def parent_folders(projects_dir, project_dir):
    """Transcript folders of the project's parent directories, nearest first."""
    found = []
    parent_dir = os.path.dirname(project_dir)
    while parent_dir and parent_dir != os.path.dirname(parent_dir):
        pexact, _ = find_project_folders(projects_dir, parent_dir, False)
        if pexact and pexact not in found:
            found.append(pexact)
        parent_dir = os.path.dirname(parent_dir)
    return found


def hashed_folders(projects_dir, project_dir, exclude):
    """Folders that may be the project's under a shortened name: some Claude
    Code versions cut long folder names and append a hash. A candidate's name,
    without a trailing -<hash>, must be a prefix (of 32+ characters) of the
    project's folder name. Sessions read from these are checked by cwd."""
    try:
        names = [n for n in os.listdir(projects_dir) if os.path.isdir(os.path.join(projects_dir, n))]
    except OSError:
        return []
    variants = [v.lower() for v in encode_variants(project_dir)]
    out = []
    for n in names:
        if n in exclude:
            continue
        m = re.match(r"^(.+?)-+[A-Za-z0-9]{4,}$", n)
        stem = m.group(1).lower() if m else ""
        if len(stem) >= 32 and any(v.startswith(stem) and v != stem for v in variants):
            out.append(n)
    return sorted(out)


def norm_path(p):
    p = p.replace("\\", "/")
    return (os.path.normpath(p).replace("\\", "/") if p else p).rstrip("/").lower()


def project_roots(project_dir):
    roots = {norm_path(os.path.abspath(project_dir))}
    try:
        roots.add(norm_path(os.path.realpath(project_dir)))
    except OSError:
        pass
    return roots


def under(path, roots):
    """True when `path` is one of `roots` or inside one of them."""
    if not isinstance(path, str) or not path:
        return False
    p = norm_path(path)
    return any(p == r or p.startswith(r + "/") for r in roots)


def folder_is_subdir(folder, project_dir):
    """True when a sub-project folder name maps back to a directory that
    exists inside the project (used only for sessions that record no cwd)."""
    name = folder.lower()
    for v in encode_variants(project_dir):
        base = v.lower() + "-"
        if name.startswith(base):
            rest = name[len(base):]
            break
    else:
        return False

    def walk(d, rem, depth):
        if not rem:
            return True
        if depth > 12:
            return False
        try:
            entries = os.listdir(d)
        except OSError:
            return False
        for e in entries:
            m = re.sub(r"[^A-Za-z0-9]", "-", e).lower()
            if (rem == m or rem.startswith(m + "-")) and os.path.isdir(os.path.join(d, e)):
                if walk(os.path.join(d, e), rem[len(m) + 1:], depth + 1):
                    return True
        return False

    return walk(project_dir, rest, 0)


def session_belongs(s, kind, roots, project_dir):
    """Decide whether a session read from a folder of the given kind is about
    the project. project: unless every recorded cwd is outside it (a name
    collision); subproject or hashed: some recorded cwd is the project or a
    folder inside it; parent: a recorded cwd or a written file is inside it.
    A session that records no cwd at all is judged by the files it wrote and,
    for a sub-project folder, by whether the folder name maps to a directory
    inside the project."""
    cwd_inside = any(under(c, roots) for c in s["cwds"])
    if kind == "project":
        return cwd_inside or not s["cwds"]
    writes_inside = any(under(w[1], roots) for w in s["writes"])
    if kind == "parent":
        return cwd_inside or writes_inside
    if s["cwds"]:
        return cwd_inside
    return writes_inside or (kind == "subproject" and folder_is_subdir(s["folder"], project_dir))


# ------------------------------------------------------------- parsing

def user_text(message):
    """Return the human-typed text of a user message, or '' for tool results."""
    if isinstance(message, str):
        return message
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


CMD_SUBST_HEREDOC_RE = re.compile(
    r"\$\(\s*cat\s*<<-?\s*(['\"]?)(\w+)\1[ \t]*\n(.*?)\n[ \t]*\2[ \t]*\n?\s*\)", re.S)


def shell_segments(command):
    """Split a shell (or PowerShell) command line into simple commands.

    Returns a list of (words, stdin_texts). Words have their quotes removed;
    a "$(cat <<EOF ... EOF)" substitution is replaced by the heredoc body (what
    the shell would pass); other substitutions are kept as written. A heredoc
    (<<EOF ... EOF) or here-string (<<< word) belongs to the simple command
    that declares it. Commands are separated by unquoted newlines, ;, &, &&,
    || and |. This is a best-effort reader, not a full shell parser."""
    segs = []
    words, stdin, pending = [], [], []
    cur, in_word = [], False
    i, n = 0, len(command)

    def end_word():
        nonlocal cur, in_word
        if in_word:
            words.append("".join(cur))
        cur, in_word = [], False

    def end_segment():
        nonlocal words, stdin
        end_word()
        if words or stdin:
            segs.append((words, stdin))
        words, stdin = [], []

    def substitution(j):
        """Read $( ... ) starting at command[j]; return (text, next index)."""
        m = CMD_SUBST_HEREDOC_RE.match(command, j)
        if m:
            return m.group(3), m.end()
        depth, k, quote = 0, j + 1, None
        while k < n:
            ch = command[k]
            if quote:
                if ch == quote:
                    quote = None
                elif ch == "\\" and quote == '"':
                    k += 1
            elif ch in "'\"":
                quote = ch
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return command[j:k + 1], k + 1
            k += 1
        return command[j:], n

    while i < n:
        ch = command[i]
        if ch == "'":
            k = command.find("'", i + 1)
            k = n if k < 0 else k
            cur.append(command[i + 1:k])
            in_word, i = True, k + 1
            continue
        if ch == '"':
            i += 1
            in_word = True
            while i < n and command[i] != '"':
                if command[i] == "\\" and i + 1 < n and command[i + 1] in '"\\$`\n':
                    if command[i + 1] != "\n":
                        cur.append(command[i + 1])
                    i += 2
                elif command.startswith("$(", i):
                    text, i = substitution(i)
                    cur.append(text)
                else:
                    cur.append(command[i])
                    i += 1
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            if command[i + 1] != "\n":
                cur.append(command[i + 1])
                in_word = True
            i += 2
            continue
        if command.startswith("$(", i):
            text, i = substitution(i)
            cur.append(text)
            in_word = True
            continue
        if ch == "#" and not in_word:
            k = command.find("\n", i)
            i = n if k < 0 else k
            continue
        if command.startswith("<<<", i):
            end_word()
            i += 3
            m = re.compile(r"\s*(\"([^\"]*)\"|'([^']*)'|(\S+))").match(command, i)
            if m:
                stdin.append(next(g for g in m.groups()[1:] if g is not None))
                i = m.end()
            continue
        if command.startswith("<<", i):
            end_word()
            m = re.compile(r"<<-?\s*(['\"]?)(\w+)\1").match(command, i)
            if m:
                pending.append(m.group(2))
                i = m.end()
            else:
                i += 2
            continue
        if ch == "\n":
            end_word()
            i += 1
            if pending:
                for delim in pending:
                    body = []
                    while i < n:
                        k = command.find("\n", i)
                        line = command[i:] if k < 0 else command[i:k]
                        i = n if k < 0 else k + 1
                        if line.strip() == delim:
                            break
                        body.append(line)
                    stdin.append("\n".join(body))
                pending = []
            end_segment()
            continue
        if ch in ";&|":
            end_segment()
            i += 2 if command[i:i + 2] in ("&&", "||", "|&", ";;") else 1
            continue
        if ch in " \t\r":
            end_word()
            i += 1
            continue
        cur.append(ch)
        in_word = True
        i += 1
    end_segment()
    return segs


def first_line(text):
    text = text.strip()
    m = re.match(r"^@(['\"]?)\r?\n(.*)\r?\n\1?@$", text, re.S)  # PowerShell here-string
    if m:
        text = m.group(2)
    return next((l.strip() for l in text.splitlines() if l.strip()), "")


def commit_messages(command):
    """Pull commit subjects out of a shell command that runs `git commit`.

    Understands -m MSG, -mMSG, --message MSG, --message=MSG, combined short
    flags such as -am or -qm, repeated -m (the first is the subject), and
    -F - / --file=- fed by a heredoc or here-string of the same command."""
    msgs = []
    if "git" not in command or "commit" not in command:
        return msgs
    for words, stdin in shell_segments(command):
        gi = next((k for k, w in enumerate(words) if os.path.basename(w.replace("\\", "/")).lower() in ("git", "git.exe")), None)
        if gi is None:
            continue
        k = gi + 1
        while k < len(words) and words[k].startswith("-"):  # git's own options
            k += 2 if words[k] in ("-C", "-c", "--git-dir", "--work-tree", "--namespace") else 1
        if k >= len(words) or words[k] != "commit":
            continue
        args = words[k + 1:]
        message, from_stdin = None, False
        j = 0
        while j < len(args) and message is None:
            w = args[j]
            nxt = args[j + 1] if j + 1 < len(args) else None
            if w == "--":
                break
            if w in ("--message", "--file", "--reuse-message", "--reedit-message", "--template",
                     "--author", "--date", "--cleanup", "--fixup", "--squash", "--trailer"):
                if w == "--message":
                    message = nxt
                elif w == "--file" and nxt == "-":
                    from_stdin = True
                j += 2
                continue
            if w.startswith("--message="):
                message = w[len("--message="):]
            elif w == "--file=-":
                from_stdin = True
            elif w.startswith("-") and not w.startswith("--") and len(w) > 1:
                cluster = w[1:]
                for ci, flag in enumerate(cluster):
                    if flag in "mFCct":
                        rest = cluster[ci + 1:]
                        val = rest if rest else nxt
                        if not rest:
                            j += 1
                        if flag == "m":
                            message = val
                        elif flag == "F" and val == "-":
                            from_stdin = True
                        break
                    if flag in "Su":
                        break  # optional value attached to the flag
            j += 1
        if message is not None:
            first = first_line(message)
            if first and not first.startswith("$("):
                msgs.append(first)
        elif from_stdin and stdin:
            first = first_line(stdin[0])
            if first:
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
        "slash_commands": Counter(),
        "cwds": set(),
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
    if isinstance(rec.get("cwd"), str) and rec["cwd"]:
        s["cwds"].add(rec["cwd"])
    if rec.get("isSidechain"):
        return
    uid = rec.get("uuid")
    if uid:
        if uid in seen_uuid:
            return
        seen_uuid.add(uid)
    msg = rec.get("message")
    if typ == "user":
        if rec.get("isMeta") or rec.get("isCompactSummary"):
            return
        text = user_text(msg).strip()
        cmd = SLASH_COMMAND_RE.search(text)
        if cmd:
            s["slash_commands"][cmd.group(1) if cmd.group(1).startswith("/") else "/" + cmd.group(1)] += 1
            return
        text = LEADING_REMINDERS_RE.sub("", text)
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


SOURCE_NOTES = {
    "parent": "parent-folder session, started outside the project; it may also cover other work",
    "subproject": "session started in a sub-folder of the project",
    "hashed": "session from a folder with a shortened name, matched by its recorded cwd",
}


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
        if s.get("source") in SOURCE_NOTES:
            a("- Source: %s (%s)" % (SOURCE_NOTES[s["source"]], mask(s["folder"])))
        if s["title"]:
            a("- Title (auto-generated): %s" % mask(s["title"]))
        a("- Span: %s %s to %s %s" % (day(s["first_ts"]), hhmm(s["first_ts"]), day(s["last_ts"]), hhmm(s["last_ts"])))
        a("- Prompts: %d, assistant turns: %d%s" % (
            len(s["prompts"]), s["assistant_turns"],
            ", models: " + ", ".join(m for m, _ in s["models"].most_common(3)) if s["models"] else ""))
        if s["branches"]:
            a("- Git branches seen: %s" % mask(", ".join(sorted(s["branches"]))))
        if s.get("slash_commands"):
            a("- Slash commands: %s" % mask(", ".join("%s%s" % (c, " (x%d)" % k if k > 1 else "")
                                                     for c, k in s["slash_commands"].most_common())))
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
                    help="also read sessions started from a parent directory (e.g. a workspace holding several "
                         "projects); only those whose recorded cwd or written files are inside the project are kept, "
                         "and they are labelled as parent-folder sessions")
    ap.add_argument("--include-subprojects", action="store_true",
                    help="also read transcript folders of sub-folders of the project; a session is kept only when "
                         "its recorded cwd is the project or a folder inside it (this excludes siblings such as "
                         "myproj-v2, whose folder name also starts with the project's)")
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

    roots = project_roots(project_dir)
    exact, related = find_project_folders(projects_dir, project_dir, args.include_subprojects)
    sources = [(exact, "project")] if exact else []
    if args.include_subprojects:
        sources += [(r, "subproject") for r in related]
    if not os.path.isdir(projects_dir):
        warn("transcripts folder not found: %s" % projects_dir.replace("\\", "/"))
        parents = []
    else:
        parents = parent_folders(projects_dir, project_dir)
        if not exact:
            hashed = hashed_folders(projects_dir, project_dir, set(parents) | set(related))
            if hashed:
                warn("no folder with the project's exact name; checking %d folder(s) with a shortened name by the "
                     "cwd recorded in their sessions: %s" % (len(hashed), ", ".join(hashed[:4])))
            sources += [(h, "hashed") for h in hashed]
        if parents and args.include_parents:
            sources += [(pf, "parent") for pf in parents]
            warn("reading sessions started from parent folder(s) %s; only those that worked inside the project "
                 "are kept" % ", ".join(parents))
        elif parents:
            warn("sessions were started from parent folder(s) (%s); add --include-parents to read the ones that "
                 "worked inside this project" % ", ".join(parents))
        if not exact and not any(k == "hashed" for _, k in sources):
            warn("no transcript folder for %s; tried: %s" % (project_dir.replace("\\", "/"), ", ".join(encode_variants(project_dir)[:3])))
    if related and not args.include_subprojects:
        warn("%d folder(s) of sub-projects exist; add --include-subprojects to read them: %s"
             % (len(related), ", ".join(related[:4])))
    folders = [f for f, _ in sources]

    sessions = []
    dropped = Counter()
    for folder, kind in sources:
        fdir = os.path.join(projects_dir, folder)
        try:
            names = sorted(n for n in os.listdir(fdir) if n.endswith(".jsonl"))
        except OSError as exc:
            warn("cannot list %s (%s)" % (fdir, exc))
            continue
        for n in names:
            sess = parse_session(os.path.join(fdir, n))
            sess["folder"], sess["source"] = folder, kind
            if session_belongs(sess, kind, roots, project_dir):
                sessions.append(sess)
            else:
                dropped[kind] += 1
    for kind, count in sorted(dropped.items()):
        warn("%d session(s) from %s folder(s) skipped: %s" % (count, kind, {
            "project": "every cwd they record is outside the project (another path with the same folder name)",
            "parent": "neither their recorded cwd nor the files they wrote are inside the project",
        }.get(kind, "they record no cwd inside the project (e.g. a sibling such as name-v2)")))
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
                "files_written": sorted({mask(project_relative(w[1], project_dir)) for w in s["writes"]}),
                "source": s.get("source", "project"), "folder": s.get("folder", ""),
                "slash_commands": dict(s["slash_commands"]),
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
