"""Read the posting text of asset-manager postings and count ESG terms in it.

Titles miss a lot (a "Senior Analyst" on a stewardship team, a compliance role that is about SFDR), so for
asset managers only, each posting's description is fetched once from the employer's own job-board API (the same
public Workday service the daily run already uses) and scanned. The result is a few numbers per posting kept in
data/enrich.csv; the text itself is not stored. A fetch that fails is simply retried on a later run.

Run a backfill:  uv run python -m jobwatcher.enrich [--limit N]
"""
import argparse
import csv
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

from .build import BY_NAME, DATA, ENRICH_PATH, build_history, load_enrich, load_raw
from .sources import HEADERS, TIMEOUT, workday_base
from .titlerule import RISK_TITLE

FIELDS = ["posting_id", "fetched", "strong", "terms"]

# Terms that, in the body of a posting, point at ESG / stewardship / sustainable-finance work.
STRONG = re.compile(
    r"\b(esg|environmental,? social|stewardship|proxy voting|responsible invest\w*|sustainab\w* invest\w*|"
    r"impact invest\w*|climate (?:risk|change|transition)|net[- ]zero|tcfd|sfdr|issb|csrd|greenwash\w*|"
    r"corporate governance|sustainable finance|sustainability[- ]linked)\b", re.I)
TAGS = re.compile(r"<[^>]+>")


def scan(text):
    """Return (number of strong-term mentions, 'term:count;...' for the distinct terms, most frequent first)."""
    hits = [m.group(1).lower() for m in STRONG.finditer(text or "")]
    counts = {}
    for h in hits:
        counts[h] = counts.get(h, 0) + 1
    terms = ";".join(f"{k}:{v}" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return len(hits), terms


def description_url(src, url):
    """The Workday detail endpoint for a posting, derived from its public link."""
    path = url[len(f"{workday_base(src)}/{src['site']}"):]
    return f"{workday_base(src)}/wday/cxs/{src['tenant']}/{src['site']}{path}"


def fetch_text(src, url):
    r = requests.get(description_url(src, url), headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    info = r.json().get("jobPostingInfo") or {}
    return html.unescape(TAGS.sub(" ", info.get("jobDescription") or ""))


def candidates(rows, cache):
    """Open asset-manager postings with no cached result: risk and compliance roles first, then newest first."""
    todo = [r for r in rows if r["status"] == "open" and r["employer_type"] == "asset manager"
            and r["posting_id"] not in cache and r["source"] in BY_NAME
            and BY_NAME[r["source"]]["ats"] == "workday"]
    todo.sort(key=lambda r: r["first_seen"], reverse=True)
    return sorted(todo, key=lambda r: not RISK_TITLE.search((r["title"] or "").lower()))


def enrich(rows, path=ENRICH_PATH, limit=None, workers=2, pause=1.0, fetch=fetch_text, today=None):
    """Fetch and scan new candidates. Returns (fetched, failed). Never raises on a fetch error."""
    cache = load_enrich(path)
    todo = candidates(rows, cache)
    if limit is not None:
        todo = todo[:limit]
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stats = {"failed": 0}
    streak = {}        # source name -> consecutive failures
    blocked = set()    # sources that refused us (403/429) or kept failing: left alone for the rest of this run
    results = []

    def work(r):
        name = r["source"]
        if name in blocked:
            return None
        try:
            text = fetch(BY_NAME[name], r["url"])
            streak[name] = 0
            time.sleep(pause)
            return r["posting_id"], *scan(text)
        except Exception as e:
            stats["failed"] += 1
            streak[name] = streak.get(name, 0) + 1
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (403, 429) or streak[name] >= 5:  # asked to stop, or clearly not working: stop asking
                blocked.add(name)
            return None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = [x for x in pool.map(work, todo) if x]
    if results:
        new_file = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f, lineterminator="\n")
            if new_file:
                w.writerow(FIELDS)
            for pid, strong, terms in results:
                w.writerow([pid, today, strong, terms])
    enrich.blocked = sorted(blocked)
    return len(results), stats["failed"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="fetch at most this many postings")
    args = ap.parse_args()
    rows = build_history(load_raw(DATA / "raw"), enrich=load_enrich())
    todo = len(candidates(rows, load_enrich()))
    print(f"{todo} asset-manager postings need their text read" + (f"; fetching {args.limit}" if args.limit else ""))
    done, failed = enrich(rows, limit=args.limit)
    print(f"fetched {done}, failed {failed}" + (f"; stopped asking: {", ".join(enrich.blocked)}" if enrich.blocked else ""))


if __name__ == "__main__":
    main()
