"""Fetch and save the detail response of Workday postings that need it, so the build can read them.

Two groups of postings need their detail response:
  * open asset-manager postings, whose text is scanned for ESG terms (titles miss a lot: a "Senior Analyst" on a
    stewardship team, a compliance role that is about SFDR);
  * open postings whose list location is only "N Locations", whose full location list is in the detail response.

Each response is stored once, compressed, as data/raw/details/<source>/<source id>.json.gz. The build computes
term counts, the location list and the start date from those files, so history.csv is rebuilt from the raw
folder alone and a change to the term list reaches every posting already read. The one exception is
data/enrich.csv, the term counts of postings read before the descriptions were saved: it is only a fallback and
shrinks as those postings are fetched again (they are fetched first).

Run a backfill:  uv run python -m jobwatcher.enrich [--limit N]
"""
import argparse
import gzip
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone

from .build import (BY_NAME, DATA, DETAILS_DIR, ENRICH_PATH, build_history, detail_ids, details_path,
                    load_all_enrich, load_enrich, load_raw)
from .sources import HEADERS, SESSION, TIMEOUT, workday_base
from .terms import STRONG, TAGS, plain_text, scan  # noqa: F401  (re-exported: tests and callers import them here)
from .titlerule import RISK_TITLE

MULTI_LOCATION = re.compile(r"^\d+ locations?$", re.I)


def description_url(src, url):
    """The Workday detail endpoint for a posting, derived from its public link."""
    path = url[len(f"{workday_base(src)}/{src['site']}"):]
    return f"{workday_base(src)}/wday/cxs/{src['tenant']}/{src['site']}{path}"


def fetch_detail(src, url):
    """The posting's detail response, trimmed to jobPostingInfo (the rest is other postings and the employer)."""
    r = SESSION.get(description_url(src, url), headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return {"jobPostingInfo": r.json().get("jobPostingInfo") or {}}


def save_detail(source, source_id, detail, root=DETAILS_DIR):
    path = details_path(source, source_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(json.dumps(detail, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def needs_detail(r):
    """Which open Workday postings should have their detail response saved."""
    if r["status"] != "open" or r["source"] not in BY_NAME or BY_NAME[r["source"]]["ats"] != "workday":
        return False
    return r["employer_type"] == "asset manager" or bool(MULTI_LOCATION.match(r["location"] or ""))


def candidates(rows, have, legacy=frozenset(), blocked=frozenset()):
    """Postings that need a detail file and lack one. Order: postings read before descriptions were saved (their
    flags rest on a file the raw folder cannot rebuild), then risk and compliance titles, then newest first."""
    todo = [r for r in rows if needs_detail(r) and r["posting_id"] not in have and r["source"] not in blocked]
    todo.sort(key=lambda r: r["first_seen"], reverse=True)
    return sorted(todo, key=lambda r: (r["posting_id"] not in legacy,
                                       not RISK_TITLE.search((r["title"] or "").lower())))


RETRY_AFTER_DAYS = 7  # a source that refused is left alone for this long


def blocked_sources(root, today):
    """Sources that refused recently (recorded in details/_blocked.json as source -> date of refusal)."""
    path = root / "_blocked.json"
    if not path.exists():
        return set()
    cutoff = (date.fromisoformat(today) - timedelta(days=RETRY_AFTER_DAYS)).isoformat()
    return {s for s, d in json.loads(path.read_text(encoding="utf-8")).items() if d > cutoff}


def record_blocked(root, today, names):
    path = root / "_blocked.json"
    seen = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**seen, **{n: today for n in names}}, indent=1, sort_keys=True), encoding="utf-8")


def enrich(rows, limit=None, workers=2, pause=1.0, fetch=fetch_detail, root=DETAILS_DIR, today=None,
           legacy_path=ENRICH_PATH):
    """Fetch and save details for new candidates. Returns (fetched, failed, blocked): the counts and the sources
    that refused (403 or 429) or kept failing and were left alone for the rest of the run. Never raises on a
    fetch error. The limit is applied after sources already known to refuse are removed."""
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    have = detail_ids(root)
    legacy = set(load_enrich(legacy_path))
    known_blocked = blocked_sources(root, today)
    todo = candidates(rows, have, legacy, known_blocked)
    if limit is not None:
        todo = todo[:limit]
    lock = threading.Lock()
    failed, streak, blocked, fetched = [0], {}, set(known_blocked), []

    def work(r):
        name = r["source"]
        with lock:
            if name in blocked:
                return
        try:
            detail = fetch(BY_NAME[name], r["url"])
            save_detail(name, r["source_id"], detail, root)
            with lock:
                streak[name] = 0
                fetched.append(r["posting_id"])
            time.sleep(pause)
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            with lock:
                failed[0] += 1
                streak[name] = streak.get(name, 0) + 1
                if code in (403, 429) or streak[name] >= 5:  # asked to stop, or clearly not working
                    blocked.add(name)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    new_blocked = sorted(blocked - known_blocked)
    if new_blocked:
        record_blocked(root, today, new_blocked)
    return len(fetched), failed[0], new_blocked, sorted(fetched)


def write_fetch_log(date, fetched, failed, blocked):
    """Record this run's detail fetches beside the day's results (data/raw/<date>/details.json)."""
    day_dir = DATA / "raw" / date
    if day_dir.exists():
        (day_dir / "details.json").write_text(json.dumps(
            {"fetched": len(fetched), "failed": failed, "blocked": blocked, "posting_ids": fetched}, indent=1),
            encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="fetch at most this many postings")
    args = ap.parse_args()
    rows = build_history(load_raw(DATA / "raw"), enrich=load_all_enrich())
    todo = len(candidates(rows, detail_ids()))
    print(f"{todo} postings need their detail response saved" + (f"; fetching {args.limit}" if args.limit else ""))
    done, failed, blocked, ids = enrich(rows, limit=args.limit)
    write_fetch_log(datetime.now(timezone.utc).strftime("%Y-%m-%d"), ids, failed, blocked)
    print(f"fetched {done}, failed {failed}" + (f"; stopped asking: {', '.join(blocked)}" if blocked else ""))


if __name__ == "__main__":
    main()
