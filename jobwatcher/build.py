"""Build data/history.csv and data/status.json from the raw files alone.

Run:  uv run python -m jobwatcher.build
"""
import csv
import gzip
import json
import re
from pathlib import Path

from .locations import all_places, country_of, normalize_location
from .sources import COLUMNS, NORMALIZE, SOURCES, employer_type
from .terms import plain_text, scan
from .titlerule import esg_via, in_role

DATA = Path(__file__).resolve().parent.parent / "data"
HISTORY_COLUMNS = COLUMNS + ["location_norm", "country", "remote", "locations_all", "in_role", "employer_type", "text_read", "am_esg", "esg_via", "esg_terms", "first_run", "first_seen", "last_seen", "status", "removed_date"]
BY_NAME = {s["name"]: s for s in SOURCES}
ENRICH_PATH = DATA / "enrich.csv"  # legacy: term counts of postings read before descriptions were saved
DETAILS_DIR = DATA / "raw" / "details"  # one saved detail response per posting: <source>/<source id>.json.gz


def details_path(source, source_id, root=DETAILS_DIR):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", str(source_id))
    return Path(root) / source / f"{safe}.json.gz"


def detail_ids(root=DETAILS_DIR):
    """posting_ids that have a saved detail file (a directory listing only; nothing is parsed)."""
    return {f"{d.name}:{p.name[:-len('.json.gz')]}" for d in Path(root).glob("*") if d.is_dir()
            for p in d.glob("*.json.gz")}


def load_details(root=DETAILS_DIR):
    """posting_id -> {"strong", "terms", "locations", "posted", "detail": True}, computed from the saved
    responses. The term counts are recomputed on every build, so a change to the term list reaches every
    posting. Files are read one at a time and not kept."""
    out = {}
    for d in sorted(Path(root).glob("*")):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.json.gz")):
            try:
                info = json.loads(gzip.decompress(p.read_bytes())).get("jobPostingInfo") or {}
            except (OSError, ValueError):
                continue
            strong, terms = scan(plain_text(info.get("jobDescription")))
            locs = [info.get("location")] + list(info.get("additionalLocations") or [])
            out[f"{d.name}:{p.name[:-len('.json.gz')]}"] = {
                "strong": strong, "terms": terms, "detail": True,
                "locations": [l for l in locs if l], "posted": (info.get("startDate") or "")[:10]}
    return out


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
                    cur.update({k: v for k, v in row.items() if v != ""})  # a blank listing keeps the earlier value
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
        r["text_read"] = pid in enrich
        if not r["posted_date"] and e.get("posted"):
            r["posted_date"] = e["posted"]
        places, remote = [], False
        for text in (e.get("locations") or [r["location"]]):
            place, is_remote = normalize_location(text)
            remote = remote or is_remote
            for q in (all_places(text) if ";" in text else [place]):
                if q and q not in places:
                    places.append(q)
        r["location_norm"] = places[0] if places else ""
        r["country"] = country_of(r["location_norm"])
        r["locations_all"] = ";".join(places) if len(places) > 1 else ""
        r["remote"] = remote
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
        "sources": [{k: s[k] for k in ("name", "employer", "ok", "count", "error", "last_ok", "suspect") if k in s}
                    for s in results],
    }


def load_all_enrich():
    """Saved detail files win; the legacy enrich.csv fills in postings whose description was never saved."""
    return {**load_enrich(), **load_details()}


def main():
    days = load_raw(DATA / "raw")
    rows = build_history(days, enrich=load_all_enrich())
    write_history(rows, DATA / "history.csv")
    print(f"history.csv: {len(rows)} postings from {len(days)} day(s) of raw files")


if __name__ == "__main__":
    main()
