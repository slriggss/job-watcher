"""The daily run: fetch every source, build the history, write status, open the GitHub Issue.

Run:  uv run python -m jobwatcher.pipeline [--date YYYY-MM-DD] [--no-issue]
"""
import argparse
import gzip
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .build import DATA, build_history, build_status, load_raw, write_history
from .sources import FETCH, NORMALIZE, SOURCES

ISSUE_LIMIT = 60000  # GitHub caps an issue body at 65,536 characters


def fetch_source(src):
    """Return (name, raw or None, result). A failure is a result, never an exception."""
    try:
        raw = FETCH[src["ats"]](src)
        count = len(NORMALIZE[src["ats"]](src, raw))
        return src["name"], raw, {"name": src["name"], "ok": True, "count": count, "error": ""}
    except Exception as e:  # one source failing must not stop the run
        return src["name"], None, {"name": src["name"], "ok": False, "count": 0,
                                   "error": f"{type(e).__name__}: {e}"[:300]}


def fetch_all(date):
    """Replace the day's raw files with a fresh pull. Returns the per-source results."""
    day_dir = DATA / "raw" / date
    if day_dir.exists():
        shutil.rmtree(day_dir)
    day_dir.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        fetched = list(pool.map(fetch_source, SOURCES))
    results = []
    for name, raw, result in fetched:
        if raw is not None:
            with gzip.GzipFile(day_dir / f"{name}.json.gz", "wb", mtime=0) as f:
                f.write(json.dumps(raw, separators=(",", ":")).encode())
        results.append(result)
    (day_dir / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    if not any(r["ok"] for r in results):  # nothing fetched: this is not a day with a raw file
        shutil.rmtree(day_dir)
    return results


def issue_body(rows, date, results, limit=ISSUE_LIMIT):
    new = [r for r in rows if r["first_seen"] == date and not r["first_run"]]
    gone = [r for r in rows if r["removed_date"] == date]
    failed = [r["name"] for r in results if not r["ok"]]
    key = lambda r: (not r["in_role"], r["employer"], r["title"])

    def section(title, items):
        lines = [f"## {title} ({len(items)})", ""]
        used = 0
        for i, r in enumerate(sorted(items, key=key)):
            line = f"- [{r['title']}]({r['url']}) — {r['employer']}" + (f", {r['location']}" if r["location"] else "")
            line += " **(in role)**" if r["in_role"] else ""
            used += len(line)
            if used > limit // 2:
                lines.append(f"- … and {len(items) - i} more (see data/history.csv)")
                break
            lines.append(line)
        if not items:
            lines.append("None.")
        return "\n".join(lines)

    head = f"Run for {date}: {len(new)} new, {len(gone)} removed."
    if failed:
        head += f"\n\nSources that failed today: {', '.join(failed)}."
    return "\n\n".join([head, section("New postings", new), section("Removed postings", gone)])


def gh(*args, body=None):
    """Run gh. A body goes through stdin (not argv) and a failure reports gh's own error text."""
    cmd = ["gh", *args] + (["--body-file", "-"] if body is not None else [])
    r = subprocess.run(cmd, input=body, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"gh {' '.join(args[:2])} failed ({r.returncode}): {r.stderr.strip()[:500]}")
    return r


def update_issue(date, body):
    """Open (or update) the issue titled with the date, and close every other open run issue."""
    listing = json.loads(gh("issue", "list", "--state", "all", "--limit", "100",
                            "--json", "number,title,state").stdout)
    mine = next((i for i in listing if i["title"] == date), None)
    if mine:
        gh("issue", "edit", str(mine["number"]), body=body)
        if mine["state"] != "OPEN":
            gh("issue", "reopen", str(mine["number"]))
    else:
        gh("issue", "create", "--title", date, body=body)
    for i in listing:
        if i["state"] == "OPEN" and i["title"] != date:
            gh("issue", "close", str(i["number"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="override the UTC run date (YYYY-MM-DD)")
    ap.add_argument("--no-issue", action="store_true")
    args = ap.parse_args()
    now = datetime.now(timezone.utc)
    date = args.date or now.strftime("%Y-%m-%d")

    results = fetch_all(date)
    days = load_raw(DATA / "raw")
    rows = build_history(days)
    write_history(rows, DATA / "history.csv")
    status = build_status(rows, days, now.strftime("%Y-%m-%dT%H:%M:%SZ"), results)
    (DATA / "status.json").write_text(json.dumps(status, indent=1), encoding="utf-8")
    for r in results:
        print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['name']:<14} {r['count']:>5} {r['error']}")
    print(f"open={status['open']} new_today={status['new_today']} removed_today={status['removed_today']}")
    if not args.no_issue:
        # Never let the issue step cost the day's data: retry with a shorter body, then warn.
        for limit in (ISSUE_LIMIT, 15000, 2000):
            try:
                update_issue(date, issue_body(rows, date, results, limit))
                break
            except Exception as e:
                print(f"::warning::issue update failed with limit {limit}: {e}")


if __name__ == "__main__":
    main()
