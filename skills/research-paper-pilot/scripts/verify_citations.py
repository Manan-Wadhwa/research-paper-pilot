#!/usr/bin/env python3
"""verify_citations.py: check a BibTeX file for broken, incomplete or unverifiable references.

Why: a reference written from memory is the commonest way a paper acquires a fabricated or
blended citation. This script never edits or deletes anything; it reports what it can prove.

Offline checks (always run)
  required fields per entry type, duplicate keys, duplicate titles, "and others" or "et al"
  in an author list, bare venues (an acronym with no spelled-out name), arXiv id versus year,
  placeholder text (TODO, VERIFY, ???), authors separated by commas instead of "and".

Online checks (--online; urllib only, no API keys, 10 s timeout per request, continues on errors)
  DOI: doi.org HEAD request, then a CrossRef metadata comparison of title and first author.
  arXiv id: export.arxiv.org API, title and first author compared with the entry.
  No DOI and no arXiv id: CrossRef title search; the best hit must match title and author.

Verdict per entry: verified | mismatch | unresolved | offline-only
  verified    an external record matches the title and the first author
  mismatch    a record exists but title or author differ (read both before changing anything)
  unresolved  nothing found or the network failed (open the page by hand, or mark [VERIFY])
  offline-only  --online was not requested

Usage
  python verify_citations.py refs.bib [--online] [--out CITATION_REPORT.md] [--json] [--timeout 10]

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


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- bib parsing

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
        while j < n and depth:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
            j += 1
        body = text[body_start:j - 1]
        line = text.count("\n", 0, i) + 1
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
        fields = parse_fields(body[km.end():], strings)
        entries.append({"key": key, "type": etype, "fields": fields, "line": line})
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
    fields = {}
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
        fields[name] = val
    return fields


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


def author_list(field):
    return [a.strip() for a in re.split(r"\s+and\s+", field or "") if a.strip()]


def first_surname(field):
    al = author_list(field)
    if not al:
        return ""
    a = clean_latex(al[0])
    if a.lower() in ("others", "et al"):
        return ""
    if "," in a:
        sur = a.split(",")[0]
    else:
        sur = a.split()[-1] if a.split() else ""
    return strip_accents(sur).lower().strip()


def year_of(fields):
    for k in ("year", "date"):
        m = re.search(r"(1[89]\d\d|20\d\d)", fields.get(k, ""))
        if m:
            return int(m.group(1))
    return None


ARXIV_NEW = re.compile(r"(?<!\d)(\d{2})(\d{2})\.(\d{4,5})(?:v\d+)?(?!\d)")


def arxiv_id(fields):
    for k in ("eprint", "journal", "note", "url", "howpublished", "doi", "booktitle", "archiveprefix"):
        v = fields.get(k, "")
        if not v:
            continue
        if k == "eprint" or re.search(r"arxiv", v, re.I):
            m = ARXIV_NEW.search(v)
            if m:
                return m.group(0).split("v")[0]
    return None


def doi_of(fields):
    d = fields.get("doi", "").strip()
    if not d:
        m = re.search(r"doi\.org/(10\.\S+)", fields.get("url", ""))
        d = m.group(1) if m else ""
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I).strip().rstrip(".,}")
    return d if d.startswith("10.") else ""


def venue_of(fields):
    return fields.get("booktitle") or fields.get("journal") or fields.get("journaltitle") or ""


# ---------------------------------------------------------------- offline checks

def offline_checks(entries):
    issues = {e["key"]: [] for e in entries}
    today = datetime.date.today()
    seen_keys, seen_titles = {}, {}
    for e in entries:
        k, f, t = e["key"], e["fields"], e["type"]
        iss = issues[k]

        def add(code, level, msg):
            iss.append({"code": code, "level": level, "msg": msg})

        if k in seen_keys:
            add("DUP-KEY", "error", "key also defined at line %d (BibTeX keeps the first)" % seen_keys[k])
        seen_keys.setdefault(k, e["line"])
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
        elif au and " and " not in au and au.count(",") >= 2:
            add("AUTHOR-FORMAT", "warn", "several commas and no 'and': authors must be separated by 'and'")
        v = clean_latex(venue_of(f))
        if v and not re.search(r"arxiv|preprint|corr|ssrn|openreview|biorxiv", v, re.I):
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
            m = ARXIV_NEW.match(aid)
            ayr, amo = 2000 + int(m.group(1)), int(m.group(2))
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
        if not doi_of(f) and not aid and not f.get("url"):
            add("NO-IDENTIFIER", "info", "no DOI, arXiv id or URL to verify against")
    return issues


# ---------------------------------------------------------------- online checks

class Net:
    def __init__(self, timeout):
        self.timeout = timeout
        self.requests = 0
        self.failures = 0

    def fetch(self, url, method="GET"):
        self.requests += 1
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = r.read() if method == "GET" else b""
                return r.status, body, None
        except urllib.error.HTTPError as e:
            return e.code, b"", None
        except Exception as e:  # network down, timeout, TLS, DNS
            self.failures += 1
            return None, b"", "%s: %s" % (type(e).__name__, str(e)[:80])


def judge(entry, title, authors_text, year):
    """Compare an external record with the entry. Return (verdict, detail)."""
    f = entry["fields"]
    r = similarity(f.get("title", ""), title)
    sur = first_surname(f.get("author", ""))
    ext = strip_accents(authors_text).lower()
    author_ok = (not sur) or (sur in ext)
    if r >= 0.9 and author_ok:
        return "verified", "title match %.2f" % r
    parts = []
    if r < 0.9:
        parts.append("title similarity %.2f vs record '%s'" % (r, title[:70]))
    if not author_ok:
        parts.append("first author '%s' not in record authors" % sur)
    return "mismatch", "; ".join(parts)


def check_doi(net, entry, doi):
    url = "https://doi.org/" + urllib.parse.quote(doi, safe="/:()-._;")
    status, _, err = net.fetch(url, "HEAD")
    if err:
        return "unresolved", "doi.org unreachable (%s)" % err
    if status == 404:
        return "unresolved", "DOI %s does not resolve (HTTP 404)" % doi
    resolves = status < 400 or status in (401, 403, 405, 429, 999)
    cr_url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:()-._;")
    time.sleep(0.3)
    status2, body, err2 = net.fetch(cr_url)
    if status2 == 200:
        try:
            msg = json.loads(body.decode("utf-8", "replace"))["message"]
            title = " ".join(msg.get("title") or [""])
            auth = " ".join(a.get("family", "") for a in msg.get("author", []) or [])
            v, d = judge(entry, title, auth, None)
            return v, "DOI resolves; CrossRef: " + d
        except Exception as e:
            return "unresolved", "DOI resolves; CrossRef parse failed (%s)" % type(e).__name__
    if resolves:
        return "unresolved", "DOI resolves (HTTP %s) but no CrossRef metadata to compare; check by hand" % status
    return "unresolved", "DOI check inconclusive (HTTP %s)" % status


def check_arxiv_batch(net, entries_with_ids):
    """entries_with_ids: list of (entry, id). Return {key: (verdict, detail)}."""
    out = {}
    for start in range(0, len(entries_with_ids), 20):
        chunk = entries_with_ids[start:start + 20]
        ids = ",".join(i for _, i in chunk)
        url = "https://export.arxiv.org/api/query?max_results=%d&id_list=%s" % (len(chunk), ids)
        status, body, err = net.fetch(url)
        if start:
            time.sleep(3)
        if err or status != 200:
            for e, i in chunk:
                out[e["key"]] = ("unresolved", "arXiv API unavailable (%s)" % (err or "HTTP %s" % status))
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            for e, i in chunk:
                out[e["key"]] = ("unresolved", "arXiv API returned unreadable XML")
            continue
        ns = {"a": "http://www.w3.org/2005/Atom"}
        found = {}
        for ent in root.findall("a:entry", ns):
            eid = (ent.findtext("a:id", "", ns) or "")
            m = ARXIV_NEW.search(eid)
            title = re.sub(r"\s+", " ", ent.findtext("a:title", "", ns) or "").strip()
            if not m or title.lower() == "error":
                continue
            auths = " ".join(a.findtext("a:name", "", ns) for a in ent.findall("a:author", ns))
            found[m.group(0).split("v")[0]] = (title, auths)
        for e, i in chunk:
            if i in found:
                v, d = judge(e, found[i][0], found[i][1], None)
                out[e["key"]] = (v, "arXiv %s: %s" % (i, d))
            else:
                out[e["key"]] = ("unresolved", "arXiv id %s not found by the arXiv API" % i)
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
    auth = " ".join(a.get("family", "") for a in it.get("author", []) or [])
    v, d = judge(entry, t, auth, None)
    if v == "verified":
        return v, "CrossRef search hit %s: %s" % (it.get("DOI", "?"), d)
    if best[0] < 0.75:
        return "unresolved", "no close CrossRef hit (best similarity %.2f); preprints and workshop papers are often absent" % best[0]
    return v, "CrossRef best hit %s: %s" % (it.get("DOI", "?"), d)


def run_online(entries, timeout):
    net = Net(timeout)
    results = {e["key"]: [] for e in entries}
    arx = []
    for e in entries:
        doi = doi_of(e["fields"])
        aid = arxiv_id(e["fields"])
        if doi:
            results[e["key"]].append(check_doi(net, e, doi))
            time.sleep(0.3)
        if aid:
            arx.append((e, aid))
    if arx:
        for k, r in check_arxiv_batch(net, arx).items():
            results[k].append(r)
    for e in entries:
        if not results[e["key"]]:
            results[e["key"]].append(check_crossref_search(net, e))
            time.sleep(0.3)
    final = {}
    for k, rs in results.items():
        verdicts = [v for v, _ in rs]
        if "mismatch" in verdicts:
            v = "mismatch"
        elif "verified" in verdicts:
            v = "verified"
        else:
            v = "unresolved"
        final[k] = (v, " | ".join(d for _, d in rs))
    return final, net


# ---------------------------------------------------------------- reporting

def main():
    ap = argparse.ArgumentParser(description="Check a .bib file offline, and optionally against DOI/arXiv/CrossRef.")
    ap.add_argument("bib", help="BibTeX file")
    ap.add_argument("--online", action="store_true", help="also check entries against doi.org, arXiv and CrossRef")
    ap.add_argument("--out", help="write a Markdown report to this path (e.g. CITATION_REPORT.md)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the text report")
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds per network request (default 10)")
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
    online, net = {}, None
    if a.online:
        online, net = run_online(entries, a.timeout)
    rows = []
    for e in entries:
        k = e["key"]
        if a.online:
            verdict, detail = online[k]
        else:
            verdict, detail = "offline-only", ""
        rows.append({"key": k, "type": e["type"], "line": e["line"], "year": year_of(e["fields"]),
                     "title": clean_latex(e["fields"].get("title", ""))[:90], "verdict": verdict,
                     "online_detail": detail, "issues": issues[k]})
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    code_counts = {}
    for r in rows:
        for i in r["issues"]:
            code_counts[i["code"]] = code_counts.get(i["code"], 0) + 1
    summary = {"bib": a.bib.replace("\\", "/"), "entries": len(rows), "verdicts": counts,
               "issue_counts": code_counts, "online": a.online,
               "network_requests": net.requests if net else 0, "network_failures": net.failures if net else 0}
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
            "Verdicts: " + ", ".join("%s %d" % kv for kv in sorted(counts.items())), "",
            "| key | verdict | findings | online detail |", "|---|---|---|---|"]
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
            print("WARN: could not write %s (%s)" % (a.out, e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
