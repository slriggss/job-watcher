"""Build data/history.csv and data/status.json from the raw files alone.

Run:  uv run python -m jobwatcher.build
"""
import csv
import gzip
import json
from pathlib import Path

from .sources import COLUMNS, NORMALIZE, SOURCES, employer_type
from .titlerule import esg_via, in_role

DATA = Path(__file__).resolve().parent.parent / "data"
HISTORY_COLUMNS = COLUMNS + ["in_role", "employer_type", "am_esg", "esg_via", "esg_terms", "first_run", "first_seen", "last_seen", "status", "removed_date"]
BY_NAME = {s["name"]: s for s in SOURCES}
ENRICH_PATH = DATA / "enrich.csv"  # ESG-term counts from posting text, written by enrich.py


def load_enrich(path=ENRICH_PATH):
    """posting_id -> {"strong": int, "terms": str}; empty if no posting text has been read yet."""
    if not Path(path).exists():
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["posting_id"]: {"strong": int(r["strong"]), "terms": r["terms"]} for r in csv.DictReader(f)}


def load_raw(raw_dir):
    """Return {date: {source name: parsed raw json}} for every raw file on disk."""
    days = {}
    for day_dir in sorted(Path(raw_dir).glob("????-??-??")):
        files = {p.name[:-len(".json.gz")]: p for p in day_dir.glob("*.json.gz")}
        if files:
            days[day_dir.name] = {name: json.loads(gzip.decompress(p.read_bytes()))
                                  for name, p in files.items()}
    return days


def build_history(days, sources=None, enrich=None):
    """Apply the first-seen / last-seen / removed rules day by day. Returns rows sorted by posting_id.

    enrich is the optional {posting_id: {strong, terms}} cache of ESG terms found in posting text (enrich.py)."""
    enrich = enrich or {}
    # An identical pattern of ESG terms in 3+ postings of one employer is its standard company paragraph, not
    # something about the role, so it does not count toward a text match.
    seen = {}
    for pid, e in enrich.items():
        if e["terms"]:
            key = (pid.split(":")[0], e["terms"])
            seen[key] = seen.get(key, 0) + 1
    boilerplate = {k for k, n in seen.items() if n >= 3}
    by_name = BY_NAME if sources is None else {s["name"]: s for s in sources}
    history = {}
    first_day = {}  # source name -> date of that source's first raw file
    for date in sorted(days):
        for name, raw in days[date].items():
            src = by_name.get(name)
            if src is None:
                continue
            first_day.setdefault(name, date)
            listed = {}
            for row in NORMALIZE[src["ats"]](src, raw):
                listed[row["posting_id"]] = row
            for pid, row in listed.items():
                cur = history.get(pid)
                if cur is None:
                    history[pid] = {**row, "first_run": first_day[name] == date, "first_seen": date,
                                    "last_seen": date, "status": "open", "removed_date": ""}
                else:  # still (or again) listed: refresh the fields and the last-seen date
                    cur.update(row)
                    cur["last_seen"] = date
                    cur["status"] = "open"
                    cur["removed_date"] = ""
            for pid, cur in history.items():
                if cur["source"] == name and cur["status"] == "open" and pid not in listed:
                    cur["status"] = "removed"
                    cur["removed_date"] = date
    rows = []
    for pid in sorted(history):
        r = history[pid]
        r["in_role"] = in_role(r["title"])
        r["employer_type"] = employer_type(r["source"])
        e = enrich.get(pid, {})
        strong = 0 if (r["source"], e.get("terms", "")) in boilerplate else e.get("strong", 0)
        r["esg_via"] = esg_via(r["title"], r["employer_type"], strong)
        r["am_esg"] = bool(r["esg_via"])
        r["esg_terms"] = e.get("terms", "")
        rows.append(r)
    return rows


def write_history(rows, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HISTORY_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (str(r[k]).lower() if isinstance(r[k], bool) else r[k]) for k in HISTORY_COLUMNS})


def build_status(rows, days, run_time, results):
    """results: list of {name, ok, count} for the latest run."""
    latest = max(days) if days else ""
    return {
        "run_time": run_time,
        "first_run_date": min(days) if days else "",
        "days_with_success": len(days),
        "open": sum(1 for r in rows if r["status"] == "open"),
        "new_today": sum(1 for r in rows if r["first_seen"] == latest and not r["first_run"]),
        "removed_today": sum(1 for r in rows if r["removed_date"] == latest),
        "sources": [{"name": s["name"], "ok": s["ok"], "count": s["count"]} for s in results],
    }


def main():
    days = load_raw(DATA / "raw")
    rows = build_history(days, enrich=load_enrich())
    write_history(rows, DATA / "history.csv")
    print(f"history.csv: {len(rows)} postings from {len(days)} day(s) of raw files")


if __name__ == "__main__":
    main()
