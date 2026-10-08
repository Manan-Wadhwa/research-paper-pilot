#!/usr/bin/env python3
"""verify_citations.py: check a BibTeX file for broken, incomplete or unverifiable references.

Why: a reference written from memory is the commonest way a paper acquires a fabricated or
blended citation. This script never edits or deletes anything; it reports what it can prove.

Offline checks (always run)
  required fields per entry type, duplicate keys (also keys that differ only in case, which BibTeX
  treats as the same key), duplicate fields, malformed entries (an unclosed entry is cut at the next
  "@type{" line instead of swallowing it), duplicate titles, "and others" or "et al" in an author
  list, bare venues (an acronym with no spelled-out name; journals such as Nature or PNAS are
  complete as is), arXiv id (new 2301.12345 or old hep-th/9901001 style) versus year, placeholder
  text (TODO, VERIFY, ???), authors separated by commas instead of "and".

Online checks (--online; urllib only, no API keys, 10 s timeout per request, continues on errors)
  DOI: doi.org HEAD request, then a CrossRef metadata comparison of title and first author.
  arXiv id: export.arxiv.org API, title and first author compared with the entry.
  No DOI and no arXiv id: CrossRef title search; the best hit must match title and author.
  The first author's surname must equal a record family name as whole words ("Li" never matches
  "Williams"); a braced corporate author ({Google DeepMind}) is compared as one literal name.
  After --max-net-failures consecutive network failures (default 3) online checks stop and the
  remaining entries are reported as unresolved, "not checked (network)".

Verdict per entry: verified | mismatch | unresolved | offline-only
  verified    an external record matches the title and the first author
  mismatch    a record exists but title or author differ (read both before changing anything)
  unresolved  nothing found or the network failed (open the page by hand, or mark [VERIFY])
  offline-only  --online was not requested

Usage
  python verify_citations.py refs.bib [--online] [--out CITATION_REPORT.md] [--json] [--timeout 10]
                              [--max-net-failures 3]

Exit code is 0 unless the bib file cannot be read (then 2).
"""
import argparse
import datetime
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "research-paper-pilot-citation-check/0.1 (offline-first bib checker)"

REQUIRED = {
    "article": [["author"], ["title"], ["journal", "journaltitle"], ["year", "date"]],
    "inproceedings": [["author"], ["title"], ["booktitle"], ["year", "date"]],
    "conference": [["author"], ["title"], ["booktitle"], ["year", "date"]],
    "incollection": [["author"], ["title"], ["booktitle"], ["publisher", "year"], ["year", "date"]],
    "book": [["author", "editor"], ["title"], ["publisher"], ["year", "date"]],
    "phdthesis": [["author"], ["title"], ["school", "institution"], ["year", "date"]],
    "mastersthesis": [["author"], ["title"], ["school", "institution"], ["year", "date"]],
    "techreport": [["author"], ["title"], ["institution"], ["year", "date"]],
    "misc": [["title"], ["author", "organization", "howpublished", "url"], ["year", "date"]],
    "online": [["title"], ["url"], ["year", "date"]],
    "unpublished": [["author"], ["title"], ["note"]],
}
FULLNAME_WORDS = re.compile(
    r"\b(conference|meeting|symposium|workshop|journal|transactions|advances|review|letters|annals|"
    r"proceedings of the|international|association|society|computing|computational|linguistics|"
    r"neural|learning|systems|research|science|nature|conference on)\b", re.I)
# journals whose short title is their full name (no BARE-VENUE warning)
COMPLETE_VENUES = re.compile(
    r"(?:the )?(?:nature|science|cell|lancet|pnas|neuron|elife|plos one|jama|bmj|immunity|genetics|"
    r"bioinformatics|biometrika|biometrics|econometrica|technometrics|psychometrika|automatica|neurocomputing|"
    r"neuroimage|cognition|brain|blood|circulation|gut|development|chest|cell reports|cell systems|"
    r"molecular cell|cancer cell|genome biology|genome research|nucleic acids research|science robotics|"
    r"science translational medicine|science immunology|physical review [a-ex]|machine learning|"
    r"artificial intelligence|neural computation|neural networks|pattern recognition|ecology|evolution|"
    r"chemical science|small|nano letters|joule|matter|chem|one earth|patterns|heliyon|iscience)", re.I)


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- bib parsing

ENTRY_AT_LINE_START = re.compile(r"\n[ \t]*@\s*[A-Za-z]+\s*[({]")


def parse_bib(text):
    entries, strings = [], {}
    i, n = 0, len(text)
    while True:
        i = text.find("@", i)
        if i < 0:
            break
        m = re.match(r"@\s*([A-Za-z]+)\s*([({])", text[i:])
        if not m:
            i += 1
            continue
        etype = m.group(1).lower()
        open_ch = m.group(2)
        close_ch = "}" if open_ch == "{" else ")"
        body_start = i + m.end()
        depth, j = 1, body_start
        broken_at = None
        while j < n and depth:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            # a new "@type{" at the start of a line while this entry is still open: the entry is
            # malformed (e.g. opened with "{" and closed with ")"); stop here instead of swallowing it
            if c == "\n" and etype != "comment" and ENTRY_AT_LINE_START.match(text, j):
                broken_at = j
                break
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
            j += 1
        line = text.count("\n", 0, i) + 1
        parse_issues = []
        if broken_at is not None:
            body = text[body_start:broken_at]
            nline = text.count("\n", 0, broken_at) + 2
            parse_issues.append({"code": "MALFORMED", "level": "error", "msg": (
                "entry opened with '%s' has no matching '%s' before the next entry at line %d; "
                "BibTeX may swallow the entries that follow" % (open_ch, close_ch, nline))})
            j = broken_at + 1
        elif depth:
            body = text[body_start:n]
            parse_issues.append({"code": "MALFORMED", "level": "error",
                                 "msg": "entry is not closed before the end of the file (unbalanced '%s')" % open_ch})
        else:
            body = text[body_start:j - 1]
        i = j
        if etype in ("comment", "preamble"):
            continue
        if etype == "string":
            sm = re.match(r"\s*([A-Za-z0-9_\-]+)\s*=\s*(.*)$", body, re.S)
            if sm:
                strings[sm.group(1).lower()] = parse_value(sm.group(2).strip(), strings)[0]
            continue
        km = re.match(r"\s*([^,\s]+)\s*,?", body)
        if not km:
            continue
        key = km.group(1)
        fields, dups = parse_fields(body[km.end():], strings)
        for name in dups:
            parse_issues.append({"code": "DUP-FIELD", "level": "warn",
                                 "msg": "field '%s' appears more than once; BibTeX uses the first value" % name})
        entries.append({"key": key, "type": etype, "fields": fields, "line": line, "parse_issues": parse_issues})
    return entries


def parse_value(s, strings):
    """Parse one BibTeX value (possibly # concatenated). Return (text, rest)."""
    parts = []
    i = 0
    while i < len(s):
        while i < len(s) and s[i].isspace():
            i += 1
        if i >= len(s):
            break
        c = s[i]
        if c == "{":
            depth, j = 1, i + 1
            while j < len(s) and depth:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                j += 1
            parts.append(s[i + 1:j - 1])
            i = j
        elif c == '"':
            j, depth = i + 1, 0
            while j < len(s):
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == "{":
                    depth += 1
                elif s[j] == "}":
                    depth -= 1
                elif s[j] == '"' and depth == 0:
                    break
                j += 1
            parts.append(s[i + 1:j])
            i = j + 1
        else:
            m = re.match(r"[^\s,#}]+", s[i:])
            if not m:
                break
            tok = m.group(0)
            parts.append(strings.get(tok.lower(), tok) if not tok.isdigit() else tok)
            i += m.end()
        while i < len(s) and s[i].isspace():
            i += 1
        if i < len(s) and s[i] == "#":
            i += 1
            continue
        break
    return "".join(parts), s[i:]


def parse_fields(body, strings):
    """Return (fields, names of repeated fields). A repeated field never overwrites the first."""
    fields, dups = {}, []
    i, n = 0, len(body)
    while i < n:
        m = re.compile(r"\s*,?\s*([A-Za-z][A-Za-z0-9_\-:]*)\s*=\s*").match(body, i)
        if not m:
            nxt = body.find(",", i)
            if nxt < 0:
                break
            i = nxt + 1
            continue
        name = m.group(1).lower()
        val, rest = parse_value(body[m.end():], strings)
        consumed = len(body) - m.end() - len(rest)
        i = m.end() + consumed
        if name in fields:
            if name not in dups:
                dups.append(name)
            continue
        fields[name] = val
    return fields, dups


# ---------------------------------------------------------------- text helpers

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def clean_latex(s):
    s = re.sub(r"\\[\"'^`~=.]\s*\{?\\?([A-Za-z])\}?", r"\1", s)
    s = s.replace("\\ss", "ss").replace("\\o", "o").replace("\\aa", "a").replace("\\ae", "ae")
    s = re.sub(r"\\[A-Za-z]+\*?", " ", s)
    s = re.sub(r"[{}$\\]", "", s)
    s = s.replace("~", " ")
    return re.sub(r"\s+", " ", s).strip()


def norm_title(s):
    s = strip_accents(clean_latex(s)).lower()
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"[-_/]", " ", s)).strip()


def similarity(a, b):
    a, b = norm_title(a), norm_title(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def top_level(s, fill="_"):
    """s with every braced group (braces included) replaced by fill, so separators inside {...} are not seen."""
    out, depth = [], 0
    for c in s:
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
            out.append(fill)
            continue
        out.append(c if depth == 0 else fill)
    return "".join(out)


def author_list(field):
    """Split an author field on ' and ' outside braces ({Barnes and Noble} stays one name)."""
    field = field or ""
    top = top_level(field)
    out, start = [], 0
    for m in re.finditer(r"\s+and\s+", top):
        out.append(field[start:m.start()])
        start = m.end()
    out.append(field[start:])
    return [a.strip() for a in out if a.strip()]


def is_corporate(name):
    """{Google DeepMind}: the whole name is one braced group, a literal name with no surname."""
    name = name.strip()
    if len(name) < 3 or name[0] != "{":
        return False
    depth = 0
    for j, c in enumerate(name):
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j == len(name) - 1
    return False


PARTICLES = {"von", "van", "de", "der", "den", "di", "da", "du", "del", "della", "des", "le", "la", "dos", "das",
             "ter", "ten", "bin", "al", "el", "zu", "st", "y"}
SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}


def family_of_full(name):
    """Family name from 'Given [von] Family [Jr.]' (arXiv style)."""
    toks = [t for t in name.split() if t.lower().strip(",") not in SUFFIXES]
    if len(toks) <= 1:
        return " ".join(toks)
    for k in range(1, len(toks) - 1):
        if toks[k].lower() in PARTICLES:
            return " ".join(toks[k:])
    return toks[-1]


def name_tokens(s):
    return re.findall(r"[a-z0-9]+", strip_accents(clean_latex(s)).lower())


def first_surname(field):
    al = author_list(field)
    if not al:
        return ""
    if is_corporate(al[0]):
        return strip_accents(clean_latex(al[0])).lower().strip()
    a = clean_latex(al[0])
    if a.lower() in ("others", "et al"):
        return ""
    if "," in a:
        sur = a.split(",")[0]
    else:
        sur = family_of_full(a)
    return strip_accents(sur).lower().strip()


def contains_tokens(hay, needle):
    """True when the token list needle occurs as a contiguous run of whole tokens in hay."""
    if not needle or not hay:
        return False
    k = len(needle)
    return any(hay[i:i + k] == needle for i in range(len(hay) - k + 1))


def author_matches(field, record_authors):
    """Does the entry's first author appear among record_authors, a list of (family, full name)?

    Surnames are compared as whole tokens ('Li' does not match 'Williams'); a corporate author such
    as {Google DeepMind} is compared, whole, with the record's full names."""
    al = author_list(field)
    sur = first_surname(field)
    if not sur:
        return True
    st = name_tokens(sur)
    corporate = bool(al) and is_corporate(al[0])
    for fam, full in record_authors:
        if corporate:
            if contains_tokens(name_tokens(full or fam), st):
                return True
            continue
        ft = name_tokens(fam or family_of_full(full or ""))
        if contains_tokens(ft, st) or contains_tokens(st, ft):
            return True
    return False


def year_of(fields):
    for k in ("year", "date"):
        m = re.search(r"(1[89]\d\d|20\d\d)", fields.get(k, ""))
        if m:
            return int(m.group(1))
    return None


ARXIV_NEW = re.compile(r"(?<!\d)(\d{2})(\d{2})\.(\d{4,5})(?:v\d+)?(?!\d)")
# old-style ids (before April 2007): hep-th/9901001, math.GT/0309136, cs/0112017
ARXIV_OLD = re.compile(r"(?<![A-Za-z\-.])([a-z]+(?:-[a-z]+)?)(?:\.[A-Za-z]{2})?/(\d{2})(\d{2})(\d{3})(?:v\d+)?(?!\d)")


def find_arxiv(v):
    """Canonical arXiv id in v (old-style ids without the subject class: math/0309136), or None."""
    m = ARXIV_NEW.search(v)
    if m:
        return m.group(0).split("v")[0]
    m = ARXIV_OLD.search(v)
    if m:
        return "%s/%s%s%s" % (m.group(1), m.group(2), m.group(3), m.group(4))
    return None


def arxiv_date(aid):
    """(year, month) encoded in an arXiv id."""
    digits = aid.split("/")[1] if "/" in aid else aid
    yy, mm = int(digits[:2]), int(digits[2:4])
    if "/" in aid and yy >= 91:
        return 1900 + yy, mm
    return 2000 + yy, mm


def arxiv_id(fields):
    for k in ("eprint", "journal", "note", "url", "howpublished", "doi", "booktitle", "archiveprefix"):
        v = fields.get(k, "")
        if not v:
            continue
        if k == "eprint" or re.search(r"arxiv", v, re.I):
            aid = find_arxiv(v)
            if aid:
                return aid
    return None


def url_of(fields):
    """The entry's URL: the url field, or a \\url{...} / http link in howpublished or note."""
    if fields.get("url", "").strip():
        return fields["url"].strip()
    for k in ("howpublished", "note"):
        v = fields.get(k, "")
        m = re.search(r"\\url\s*\{([^{}]+)\}", v) or re.search(r"https?://[^\s{}]+", v)
        if m:
            return (m.group(1) if m.lastindex else m.group(0)).strip()
    return ""


def doi_of(fields):
    d = fields.get("doi", "").strip()
    if not d:
        m = re.search(r"doi\.org/(10\.\S+)", url_of(fields))
        d = m.group(1) if m else ""
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I).strip().rstrip(".,}")
    return d if d.startswith("10.") else ""


def venue_of(fields):
    return fields.get("booktitle") or fields.get("journal") or fields.get("journaltitle") or ""


# ---------------------------------------------------------------- offline checks

def offline_checks(entries):
    """Return one issue list per entry, in the order of entries (duplicate keys get their own lists)."""
    issues = [list(e.get("parse_issues", [])) for e in entries]
    today = datetime.date.today()
    seen_titles = {}
    by_lower = {}
    for idx, e in enumerate(entries):
        by_lower.setdefault(e["key"].lower(), []).append(idx)
    for idx, e in enumerate(entries):
        k, f, t = e["key"], e["fields"], e["type"]
        iss = issues[idx]

        def add(code, level, msg):
            iss.append({"code": code, "level": level, "msg": msg})

        group_idx = by_lower[k.lower()]
        first = entries[group_idx[0]]
        for o in group_idx:
            if o == idx:
                continue
            other = entries[o]
            if other["key"] == k:
                if o < idx:
                    add("DUP-KEY", "error", "key also defined at line %d (BibTeX keeps the first)" % other["line"])
                else:
                    add("DUP-KEY", "error", "key defined again at line %d (BibTeX keeps this one, the first)" % other["line"])
            else:
                add("DUP-KEY-CASE", "error", "key '%s' differs only in case from '%s' at line %d; BibTeX compares keys "
                    "case-insensitively and keeps '%s'" % (k, other["key"], other["line"], first["key"]))
        for group in REQUIRED.get(t, [["title"], ["year", "date"]]):
            if not any(f.get(g, "").strip() for g in group):
                add("MISSING", "error", "missing field: " + "/".join(group))
        nt = norm_title(f.get("title", ""))
        if nt:
            if nt in seen_titles and seen_titles[nt] != k:
                add("DUP-TITLE", "warn", "same title as entry '%s'" % seen_titles[nt])
            seen_titles.setdefault(nt, k)
        au = f.get("author", "")
        if re.search(r"\band\s+others\b|\bet\s+al\b", au, re.I):
            add("AUTHORS-TRUNCATED", "warn", "author list ends with 'and others'; fetch the full list from the venue page")
        elif au and len(author_list(au)) == 1 and top_level(au).count(",") >= 2:
            add("AUTHOR-FORMAT", "warn", "several commas and no 'and': authors must be separated by 'and'")
        v = clean_latex(venue_of(f))
        if v and not re.search(r"arxiv|preprint|corr|ssrn|openreview|biorxiv", v, re.I) and \
                not COMPLETE_VENUES.fullmatch(v.strip(" .,")):
            core = re.sub(r"\([^)]*(papers|track|volume)[^)]*\)", " ", v, flags=re.I)
            core = re.sub(r"\b(proceedings of( the)?|in|the|\d{4}|\d+(st|nd|rd|th)|annual)\b", " ", core, flags=re.I)
            core = re.sub(r"\s+", " ", core).strip(" ,.()")
            words = core.split()
            has_full = len(re.findall(r"[A-Za-z]{4,}", core)) >= 3 or FULLNAME_WORDS.search(core.replace("Proceedings", ""))
            if (len(words) <= 2 and re.fullmatch(r"[A-Z][A-Za-z\-]{1,10}( [A-Z]{2,})?|[A-Z]{2,}[- ]?\d*", core)) or not has_full:
                add("BARE-VENUE", "warn", "venue '%s' is only an acronym or short name; write the full venue name" % v)
        if re.search(r"arxiv", v, re.I) and not arxiv_id(f):
            add("ARXIV-NO-ID", "warn", "venue says arXiv but no arXiv id found")
        aid = arxiv_id(f)
        yr = year_of(f)
        if aid:
            ayr, amo = arxiv_date(aid)
            if not 1 <= amo <= 12:
                add("ARXIV-ID", "error", "arXiv id %s has an impossible month" % aid)
            elif (ayr, amo) > (today.year, today.month):
                add("ARXIV-FUTURE", "error", "arXiv id %s is dated after today" % aid)
            if yr is not None and yr < ayr:
                add("YEAR-ARXIV", "warn", "year %d is earlier than the arXiv id's year %d" % (yr, ayr))
            elif yr is not None and yr > ayr + 1:
                add("YEAR-ARXIV", "info", "year %d is later than arXiv id year %d (fine if this is the published version)" % (yr, ayr))
        if yr is not None and yr > today.year + 1:
            add("YEAR-FUTURE", "warn", "year %d is in the future" % yr)
        blob = " ".join(f.values())
        if re.search(r"\b(TODO|TBD|FIXME|XXX)\b|\[VERIFY\]|\?\?\?", blob):
            add("PLACEHOLDER", "warn", "placeholder text in a field")
        if not doi_of(f) and not aid and not url_of(f):
            add("NO-IDENTIFIER", "info", "no DOI, arXiv id or URL to verify against")
    return issues


# ---------------------------------------------------------------- online checks

NOT_CHECKED = "not checked (network)"


class Net:
    """urllib wrapper with a circuit breaker: after max_failures consecutive network failures
    (timeouts, DNS, refused; HTTP error codes do not count) it stops making requests."""

    def __init__(self, timeout, max_failures=3):
        self.timeout = timeout
        self.requests = 0
        self.failures = 0
        self.consecutive = 0
        self.max_failures = max_failures
        self.stopped = False

    def stop_note(self):
        return "%s: online checks stopped after %d consecutive network failures" % (NOT_CHECKED, self.consecutive)

    def fetch(self, url, method="GET"):
        if self.stopped:
            return None, b"", self.stop_note()
        self.requests += 1
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read() if method == "GET" else b""
                self.consecutive = 0
                return r.status, body, None
        except urllib.error.HTTPError as e:
            self.consecutive = 0
            return e.code, b"", None
        except Exception as e:  # network down, timeout, TLS, DNS
            self.failures += 1
            self.consecutive += 1
            if self.max_failures and self.consecutive >= self.max_failures:
                self.stopped = True
            return None, b"", "%s: %s" % (type(e).__name__, str(e)[:80])

    def pause(self, seconds):
        if not self.stopped:
            time.sleep(seconds)


def judge(entry, title, record_authors, year):
    """Compare an external record with the entry. record_authors: list of (family, full name).
    Return (verdict, detail)."""
    f = entry["fields"]
    r = similarity(f.get("title", ""), title)
    sur = first_surname(f.get("author", ""))
    author_ok = author_matches(f.get("author", ""), record_authors)
    if r >= 0.9 and author_ok:
        return "verified", "title match %.2f" % r
    parts = []
    if r < 0.9:
        parts.append("title similarity %.2f vs record '%s'" % (r, title[:70]))
    if not author_ok:
        parts.append("first author '%s' not in record authors" % sur)
    return "mismatch", "; ".join(parts)


def crossref_authors(item):
    out = []
    for a in item.get("author", []) or []:
        fam = a.get("family") or a.get("name") or ""
        full = " ".join(x for x in (a.get("given", ""), a.get("family", "")) if x) or a.get("name", "")
        out.append((fam, full))
    return out


def check_doi(net, entry, doi):
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:()-._;")
    status, _, err = net.fetch(url, "HEAD")
    if err:
        return "unresolved", "doi.org unreachable (%s)" % err
    if status == 404:
        return "unresolved", "DOI %s does not resolve (HTTP 404)" % doi
    resolves = status < 400 or status in (401, 403, 405, 429, 999)
    cr_url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:()-._;")
    net.pause(0.3)
    status2, body, err2 = net.fetch(cr_url)
    if status2 == 200:
        try:
            msg = json.loads(body.decode("utf-8", "replace"))["message"]
            title = " ".join(msg.get("title") or [""])
            v, d = judge(entry, title, crossref_authors(msg), None)
            return v, "DOI resolves; CrossRef: " + d
        except Exception as e:
            return "unresolved", "DOI resolves; CrossRef parse failed (%s)" % type(e).__name__
    if resolves:
        return "unresolved", "DOI resolves (HTTP %s) but no CrossRef metadata to compare; check by hand" % status
    return "unresolved", "DOI check inconclusive (HTTP %s)" % status


def check_arxiv_batch(net, entries_with_ids):
    """entries_with_ids: list of (index, entry, id). Return {index: (verdict, detail)}."""
    out = {}
    for start in range(0, len(entries_with_ids), 20):
        chunk = entries_with_ids[start:start + 20]
        if net.stopped:
            for idx, e, i in chunk:
                out[idx] = ("unresolved", net.stop_note())
            continue
        if start:
            time.sleep(3)
        ids = ",".join(sorted(set(i for _, _, i in chunk)))
        url = "https://export.arxiv.org/api/query?max_results=%d&id_list=%s" % (len(chunk), ids)
        status, body, err = net.fetch(url)
        if err or status != 200:
            for idx, e, i in chunk:
                out[idx] = ("unresolved", "arXiv API unavailable (%s)" % (err or "HTTP %s" % status))
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            for idx, e, i in chunk:
                out[idx] = ("unresolved", "arXiv API returned unreadable XML")
            continue
        ns = {"a": "http://www.w3.org/2005/Atom"}
        found = {}
        for ent in root.findall("a:entry", ns):
            eid = (ent.findtext("a:id", "", ns) or "")
            fid = find_arxiv(eid)
            title = re.sub(r"\s+", " ", ent.findtext("a:title", "", ns) or "").strip()
            if not fid or title.lower() == "error":
                continue
            auths = [(family_of_full(n), n) for n in
                     (re.sub(r"\s+", " ", a.findtext("a:name", "", ns) or "").strip() for a in ent.findall("a:author", ns))]
            found[fid] = (title, auths)
        for idx, e, i in chunk:
            if i in found:
                v, d = judge(e, found[i][0], found[i][1], None)
                out[idx] = (v, "arXiv %s: %s" % (i, d))
            else:
                out[idx] = ("unresolved", "arXiv id %s not found by the arXiv API" % i)
    return out


def check_crossref_search(net, entry):
    f = entry["fields"]
    title = clean_latex(f.get("title", ""))
    if not title:
        return "unresolved", "no title to search"
    q = title + " " + first_surname(f.get("author", ""))
    url = "https://api.crossref.org/works?rows=3&select=title,author,issued,DOI&query.bibliographic=" + urllib.parse.quote(q)
    status, body, err = net.fetch(url)
    if err or status != 200:
        return "unresolved", "CrossRef search unavailable (%s)" % (err or "HTTP %s" % status)
    try:
        items = json.loads(body.decode("utf-8", "replace"))["message"]["items"]
    except Exception:
        return "unresolved", "CrossRef search returned unreadable data"
    best = (0.0, None)
    for it in items:
        t = " ".join(it.get("title") or [""])
        r = similarity(title, t)
        if r > best[0]:
            best = (r, it)
    if not best[1]:
        return "unresolved", "no CrossRef hit for the title"
    it = best[1]
    t = " ".join(it.get("title") or [""])
    v, d = judge(entry, t, crossref_authors(it), None)
    if v == "verified":
        return v, "CrossRef search hit %s: %s" % (it.get("DOI", "?"), d)
    if best[0] < 0.75:
        return "unresolved", "no close CrossRef hit (best similarity %.2f); preprints and workshop papers are often absent" % best[0]
    return v, "CrossRef best hit %s: %s" % (it.get("DOI", "?"), d)


def run_online(entries, timeout, max_failures=3):
    """Return ([(verdict, detail)] in the order of entries, Net). Every entry is checked on its own,
    duplicate keys included. After max_failures consecutive network failures the remaining entries
    are marked 'not checked (network)' instead of waiting on more timeouts."""
    net = Net(timeout, max_failures)
    results = [[] for _ in entries]
    arx = []
    for idx, e in enumerate(entries):
        doi = doi_of(e["fields"])
        aid = arxiv_id(e["fields"])
        if doi:
            if net.stopped:
                results[idx].append(("unresolved", net.stop_note()))
            else:
                results[idx].append(check_doi(net, e, doi))
                net.pause(0.3)
        if aid:
            arx.append((idx, e, aid))
    if arx:
        for idx, r in check_arxiv_batch(net, arx).items():
            results[idx].append(r)
    for idx, e in enumerate(entries):
        if not results[idx]:
            if net.stopped:
                results[idx].append(("unresolved", net.stop_note()))
            else:
                results[idx].append(check_crossref_search(net, e))
                net.pause(0.3)
    final = []
    for rs in results:
        verdicts = [v for v, _ in rs]
        if "mismatch" in verdicts:
            v = "mismatch"
        elif "verified" in verdicts:
            v = "verified"
        else:
            v = "unresolved"
        final.append((v, " | ".join(d for _, d in rs)))
    return final, net


# ---------------------------------------------------------------- reporting

def main():
    ap = argparse.ArgumentParser(description="Check a .bib file offline, and optionally against DOI/arXiv/CrossRef.")
    ap.add_argument("bib", help="BibTeX file")
    ap.add_argument("--online", action="store_true", help="also check entries against doi.org, arXiv and CrossRef")
    ap.add_argument("--out", help="write a Markdown report to this path (e.g. CITATION_REPORT.md)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the text report")
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds per network request (default 10)")
    ap.add_argument("--max-net-failures", type=int, default=3,
                    help="stop online checks after this many consecutive network failures (default 3, 0 = never)")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not os.path.isfile(a.bib):
        print("ERROR: cannot read " + a.bib, file=sys.stderr)
        return 2
    entries = parse_bib(read_text(a.bib))
    issues = offline_checks(entries)
    online, net = [], None
    if a.online:
        online, net = run_online(entries, a.timeout, a.max_net_failures)
    rows = []
    for idx, e in enumerate(entries):
        k = e["key"]
        if a.online:
            verdict, detail = online[idx]
        else:
            verdict, detail = "offline-only", ""
        rows.append({"key": k, "type": e["type"], "line": e["line"], "year": year_of(e["fields"]),
                     "title": clean_latex(e["fields"].get("title", ""))[:90], "verdict": verdict,
                     "online_detail": detail, "issues": issues[idx]})
    n_not_checked = sum(1 for r in rows if NOT_CHECKED in r["online_detail"])
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    code_counts = {}
    for r in rows:
        for i in r["issues"]:
            code_counts[i["code"]] = code_counts.get(i["code"], 0) + 1
    summary = {"bib": a.bib.replace("\\", "/"), "entries": len(rows), "verdicts": counts,
               "issue_counts": code_counts, "online": a.online,
               "network_requests": net.requests if net else 0, "network_failures": net.failures if net else 0,
               "network_stopped": bool(net and net.stopped), "not_checked_network": n_not_checked}
    if a.json:
        print(json.dumps({"summary": summary, "entries": rows}, indent=2))
        text = None
    else:
        L = []
        L.append("verify_citations report for " + summary["bib"])
        L.append("entries parsed: %d   mode: %s" % (len(rows), "online" if a.online else "offline"))
        L.append("verdicts: " + ", ".join("%s=%d" % kv for kv in sorted(counts.items())))
        if not rows:
            L.append("WARN: no BibTeX entries found. The file may be empty, not BibTeX, or damaged.")
        if code_counts:
            L.append("offline findings: " + ", ".join("%s=%d" % kv for kv in sorted(code_counts.items())))
        if net:
            L.append("network: %d requests, %d failed" % (net.requests, net.failures))
            if net.requests and net.failures == net.requests:
                L.append("WARN: every request failed; no network? Entries are marked unresolved, not wrong.")
            if net.stopped:
                L.append("WARN: online checks stopped after %d consecutive network failures; %d entries marked "
                         "unresolved, %s. Rerun --online when the network is back." % (
                             a.max_net_failures, n_not_checked, NOT_CHECKED))
        L.append("")
        for r in rows:
            L.append("%-28s %-12s L%-4d %s" % (r["key"], r["verdict"], r["line"], r["title"][:60]))
            for i in r["issues"]:
                L.append("    [%s] %s: %s" % (i["level"], i["code"], i["msg"]))
            if r["online_detail"]:
                L.append("    online: " + r["online_detail"])
        text = "\n".join(L)
        print(text)
    if a.out:
        M = ["# Citation report", "", "Source: `%s`. Mode: %s. Entries: %d." % (
            summary["bib"], "online" if a.online else "offline", len(rows)), "",
            "Verdicts: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())), ""]
        if net and net.stopped:
            M += ["Online checks stopped after %d consecutive network failures; %d entries were %s." % (
                a.max_net_failures, n_not_checked, NOT_CHECKED), ""]
        M += ["| key | verdict | findings | online detail |", "|---|---|---|---|"]
        for r in rows:
            fnd = "; ".join("%s: %s" % (i["code"], i["msg"]) for i in r["issues"]) or "-"
            M.append("| %s | %s | %s | %s |" % (r["key"], r["verdict"], fnd.replace("|", "/"),
                                              (r["online_detail"] or "-").replace("|", "/")))
        M += ["", "A verdict of unresolved means nothing was found or the network failed, not that the reference is wrong.",
              "Mismatch means a record exists but differs; read both before changing the entry.", ""]
        try:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write("\n".join(M))
            print("wrote " + a.out.replace("\\", "/"), file=sys.stderr if a.json else sys.stdout)
        except OSError as e:
            print("WARN: could not write %s (%s)" % (a.out, e), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
