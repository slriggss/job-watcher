"""The daily run: fetch every source, build the history, write status, open the GitHub Issue.

Run:  uv run python -m jobwatcher.pipeline [--once] [--no-issue]
"""
import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .build import DATA, build_history, build_status, load_all_enrich, load_raw, write_history
from .enrich import enrich, write_fetch_log
from .sources import FETCH, MIN_SHARE_OF_TOTAL, NORMALIZE, SOURCES, reported_total

ENRICH_PER_RUN = 100  # a few postings per run, spread over days, so no employer site sees a burst of requests
ISSUE_LIMIT = 60000  # GitHub caps an issue body or a comment at 65,536 characters
ISSUE_LABEL = "daily-run"  # only issues with this label are ever closed by the run
OVERFLOW_MARK = "<!-- job-watcher:overflow -->"  # first line of every overflow comment, so a rerun can replace them


def fetch_source(src):
    """Return (name, raw or None, result). A failure is a result, never an exception."""
    try:
        raw = FETCH[src["ats"]](src)
        count = len(NORMALIZE[src["ats"]](src, raw))
        total = reported_total(raw)
        if total and count < total * MIN_SHARE_OF_TOTAL:  # a short pull would mark real postings as removed
            raise RuntimeError(f"incomplete pull: {count} postings against a reported total of {total}")
        return src["name"], raw, {"name": src["name"], "employer": src["employer"], "ok": True, "count": count, "error": ""}
    except Exception as e:  # one source failing must not stop the run
        return src["name"], None, {"name": src["name"], "employer": src["employer"], "ok": False, "count": 0,
                                   "error": f"{type(e).__name__}: {e}"[:300]}


def _write_raw(path, raw):
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(json.dumps(raw, separators=(",", ":")).encode())


def fetch_all(date, sources=None):
    """Pull every source and store the day's raw files. Returns the per-source results.

    A same-day rerun never destroys data. The new files go to a scratch folder and are swapped in only when at
    least one source succeeded. A source that fails in the rerun keeps its earlier file from the same day (its
    result says so). If every source fails, the day's existing files are left alone and the failures are written
    to results.failed.json beside them. results.json is always kept."""
    day_dir = DATA / "raw" / date
    tmp = DATA / "raw" / f".tmp-{date}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    old_results = {}
    if (day_dir / "results.json").exists():
        old_results = {r["name"]: r for r in json.loads((day_dir / "results.json").read_text(encoding="utf-8"))}
    with ThreadPoolExecutor(max_workers=6) as pool:
        fetched = list(pool.map(fetch_source, SOURCES if sources is None else sources))
    results = []
    for name, raw, result in fetched:
        earlier = day_dir / f"{name}.json.gz"
        if raw is not None:
            _write_raw(tmp / f"{name}.json.gz", raw)
        elif earlier.exists():  # keep this day's earlier good pull of the source
            shutil.copy2(earlier, tmp / earlier.name)
            result = {**result, "kept_earlier": True, "count": old_results.get(name, {}).get("count", 0)}
        results.append(result)
    if any(r["ok"] for r in results):
        (tmp / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
        if day_dir.exists():
            shutil.rmtree(day_dir)
        tmp.rename(day_dir)
    else:  # nothing fetched: keep whatever the day already has, and keep the record of the failures
        shutil.rmtree(tmp)
        day_dir.mkdir(parents=True, exist_ok=True)
        (day_dir / "results.failed.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


def day_is_done(date):
    """True when the day already has raw files from a run in which at least one source succeeded."""
    path = DATA / "raw" / date / "results.json"
    return path.exists() and any(r["ok"] for r in json.loads(path.read_text(encoding="utf-8")))


def source_health(date, results):
    """Add last_ok (the last date each source succeeded) and suspect (an ok pull whose count fell to under half
    of the source's last good day) to each result."""
    last_ok, last_count = {}, {}
    for day in sorted(p.name for p in (DATA / "raw").glob("????-??-??") if p.name < date):
        path = DATA / "raw" / day / "results.json"
        if not path.exists():
            continue
        for r in json.loads(path.read_text(encoding="utf-8")):
            if r["ok"]:
                last_ok[r["name"]], last_count[r["name"]] = day, r["count"]
    out = []
    for r in results:
        prev = last_count.get(r["name"])
        suspect = bool(r["ok"] and prev and prev >= 5 and r["count"] < prev / 2)
        out.append({**r, "last_ok": date if r["ok"] else last_ok.get(r["name"], ""), "suspect": suspect})
    return out


MD_SPECIALS = re.compile(r"([\\`*_{}\[\]<>|~])")


def md_escape(text):
    """Make outside text safe in an issue: no markup, no #123 cross-references, no @mentions."""
    text = MD_SPECIALS.sub(r"\\\1", text)
    text = re.sub(r"#(?=\d)", "#​", text)
    return text.replace("@", "@​")


def safe_url(url):
    return url if re.match(r"https?://", url or "") else ""


def _section_blocks(title, items):
    """Blocks for one section: a heading, then one block per employer with title and link per posting."""
    blocks = [f"## {title} ({len(items)})"]
    if not items:
        return blocks + ["None."]
    by_employer = {}
    for r in items:
        by_employer.setdefault(r["employer"], []).append(r)
    order = sorted(by_employer, key=lambda e: (not any(r["in_role"] for r in by_employer[e]), e))
    for employer in order:
        lines = [f"**{md_escape(employer)}** ({len(by_employer[employer])})"]
        for r in sorted(by_employer[employer], key=lambda r: (not r["in_role"], r["title"])):
            label, url = md_escape(r["title"]) or "(no title)", safe_url(r["url"])
            line = f"- [{label}]({url})" if url else f"- {label}"
            lines.append(line + (" **(in role)**" if r["in_role"] else ""))
        blocks.append("\n".join(lines))
    return blocks


def issue_parts(rows, date, results, limit=ISSUE_LIMIT):
    """The day's issue as a list of texts: the issue body first, then overflow comments. Nothing is cut."""
    new = [r for r in rows if r["first_seen"] == date and not r["first_run"]]
    gone = [r for r in rows if r["removed_date"] == date]
    failed = [r["name"] for r in results if not r["ok"]]
    head = f"Run for {date}: {len(new)} new, {len(gone)} removed."
    if failed:
        head += f"\n\nSources that failed today: {', '.join(failed)}."
    blocks = [head] + _section_blocks("New postings", new) + _section_blocks("Removed postings", gone)
    parts, current, size = [], [], 0
    for b in blocks:
        if current and size + len(b) + 2 > limit:
            parts.append("\n\n".join(current))
            current, size = [], 0
        current.append(b)
        size += len(b) + 2
    parts.append("\n\n".join(current))
    n = len(parts)
    return [parts[0]] + [f"{OVERFLOW_MARK}\n\nPostings, continued (part {i + 1} of {n})\n\n{p}"
                         for i, p in enumerate(parts[1:], start=1)]


def gh(*args, body=None):
    """Run gh. A body goes through stdin (not argv) and a failure reports gh's own error text."""
    cmd = ["gh", *args] + (["--body-file", "-"] if body is not None else [])
    r = subprocess.run(cmd, input=body, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed ({r.returncode}): {r.stderr.strip()[:500]}")
    return r


def issues_to_close(listing, date):
    """Numbers of the open run issues other than today's. Only issues with the daily-run label qualify."""
    return [i["number"] for i in listing
            if i["state"] == "OPEN" and i["title"] != date and ISSUE_LABEL in i["labels"]]


def update_issue(date, parts, run=gh):
    """Open (or update) the issue titled with the date, replace its overflow comments, and close the other
    open run issues. Issues without the daily-run label (a visitor's, a classmate's) are never touched."""
    run("label", "create", ISSUE_LABEL, "--force", "--color", "7a2f3a", "--description", "Created by the daily run")
    listing = json.loads(run("issue", "list", "--label", ISSUE_LABEL, "--state", "all", "--limit", "1000",
                             "--json", "number,title,state,labels").stdout)
    for i in listing:
        i["labels"] = [label["name"] for label in i["labels"]]
    mine = next((i for i in listing if i["title"] == date), None)
    if mine:
        number = str(mine["number"])
        run("issue", "edit", number, body=parts[0])
        if mine["state"] != "OPEN":
            run("issue", "reopen", number)
    else:
        created = run("issue", "create", "--title", date, "--label", ISSUE_LABEL, body=parts[0]).stdout
        number = created.strip().rsplit("/", 1)[-1]
    comments = json.loads(run("issue", "view", number, "--json", "comments").stdout)["comments"]
    for c in comments:  # a rerun replaces the earlier overflow comments
        if c["body"].startswith(OVERFLOW_MARK):
            comment_id = c["url"].rsplit("issuecomment-", 1)[-1]
            run("api", "-X", "DELETE", f"repos/{{owner}}/{{repo}}/issues/comments/{comment_id}")
    for text in parts[1:]:
        run("issue", "comment", number, body=text)
    for n in issues_to_close(listing, date):
        run("issue", "close", str(n))


def _write_outputs(values):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            for k, v in values.items():
                f.write(f"{k}={v}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="label today's live pull with another date (testing only; it does not fetch past data)")
    ap.add_argument("--no-issue", action="store_true", help="do not open or update the GitHub Issue")
    ap.add_argument("--once", action="store_true",
                    help="exit without fetching when today already has raw files (used by the backup run)")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    date = args.date or now.strftime("%Y-%m-%d")
    # step outputs: the commit and the issue use the date the data carries, not the date when they run
    if args.once and day_is_done(date):
        print(f"{date} already has raw files; nothing to do")
        _write_outputs({"run_date": date, "ran": "false"})
        return
    _write_outputs({"run_date": date, "ran": "true"})

    results = source_health(date, fetch_all(date))
    days = load_raw(DATA / "raw")
    rows = build_history(days, enrich=load_all_enrich())
    try:  # reading posting text is a bonus: whatever goes wrong here must not cost the day its data
        done, failed, blocked, ids = enrich(rows, limit=ENRICH_PER_RUN, today=date)
        write_fetch_log(date, ids, failed, blocked)
        print(f"posting details saved: {done} fetched, {failed} failed" + (f"; refused: {', '.join(blocked)}" if blocked else ""))
        if done:
            rows = build_history(days, enrich=load_all_enrich())
    except Exception as e:
        print(f"::warning::posting-text step failed: {type(e).__name__}: {e}")
    write_history(rows, DATA / "history.csv")
    status = build_status(rows, days, now.strftime("%Y-%m-%dT%H:%M:%SZ"), results)
    (DATA / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    for r in results:
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['name']:<14} {r['count']:>5} {'SUSPECT ' if r['suspect'] else ''}{r['error']}")
    print(f"open={status['open']} new_today={status['new_today']} removed_today={status['removed_today']}")
    if not args.no_issue:  # the workflow runs this as its own step instead (python -m jobwatcher.issue)
        update_issue(date, issue_parts(rows, date, results))


if __name__ == "__main__":
    main()
