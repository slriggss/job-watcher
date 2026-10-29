"""The Market page's numbers (market.js, run in Node) must agree with the history file,
checked against an independent calculation from the definitions in Python."""
import csv
import json
import shutil
import statistics
import subprocess
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import pytest

from jobwatcher.build import build_history, write_history

SRC = {"name": "a", "employer": "Alpha", "ats": "greenhouse", "token": "a"}
ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def board(*items):
    return {"jobs": [{"id": i, "title": t, "absolute_url": f"https://x/{i}", "location": {"name": loc}}
                     for i, t, loc in items]}


def make_days():
    d = lambda n: (date(2026, 10, 1) + timedelta(days=n)).isoformat()
    esg = lambda i, loc="NYC": (i, "ESG Analyst", loc)
    eng = lambda i, loc="Remote": (i, "Engineer", loc)
    return {
        d(0): {"a": board(eng(1), eng(2), esg(3))},                       # 1-3 are first-run
        d(1): {"a": board(eng(1), esg(3), eng(4), esg(5))},               # 2 removed(unknown start); 4, 5 new
        d(3): {"a": board(esg(3), eng(5), eng(6, "Austin"))},             # 1, 4 removed; 6 new
        d(5): {"a": board(esg(3), eng(5), eng(6, "Austin"), eng(7))},     # 7 new
        d(12): {"a": board(esg(3), eng(7), eng(8))},                      # 5, 6 removed; 8 new
    }


def expected(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    latest = max(r[k] for r in rows for k in ("first_seen", "last_seen", "removed_date"))
    D = date.fromisoformat
    fresh = [r for r in rows if r["first_run"] == "false"]
    lifetimes = [(D(r["removed_date"]) - D(r["first_seen"])).days for r in fresh if r["status"] == "removed"]
    eligible = [r for r in fresh if (D(latest) - D(r["first_seen"])).days >= 7]
    quick = [r for r in eligible if r["removed_date"] and (D(r["removed_date"]) - D(r["first_seen"])).days <= 7]
    opens = [r for r in rows if r["status"] == "open"]
    return {
        "new": Counter(r["first_seen"] for r in fresh),
        "new_role": Counter(r["first_seen"] for r in fresh if r["in_role"] == "true"),
        "removed": Counter(r["removed_date"] for r in rows if r["removed_date"]),
        "employers": Counter(r["employer"] for r in opens),
        "locations": Counter(r["location"] for r in opens),
        "median": statistics.median(lifetimes) if lifetimes else None,
        "eligible": len(eligible), "quick": len(quick),
        "share": len(quick) / len(eligible) if eligible else None,
        "open": len(opens), "latest": latest,
    }


def test_market_numbers_agree_with_history(tmp_path):
    path = tmp_path / "history.csv"
    write_history(build_history(make_days(), [SRC]), path)
    exp = expected(path)
    out = subprocess.run(["node", str(ROOT / "tests" / "market_check.js"), str(path), exp["latest"]],
                         capture_output=True, text=True, check=True)
    m = json.loads(out.stdout)
    assert dict(zip(m["days"], m["newAll"])) == {d: exp["new"].get(d, 0) for d in m["days"]}
    assert dict(zip(m["days"], m["newRole"])) == {d: exp["new_role"].get(d, 0) for d in m["days"]}
    assert dict(zip(m["days"], m["removed"])) == {d: exp["removed"].get(d, 0) for d in m["days"]}
    assert sum(m["newAll"]) == 5 and sum(m["removed"]) == 5  # hand-checked against make_days()
    assert dict(map(tuple, m["perEmployer"])) == dict(exp["employers"])
    assert dict(map(tuple, m["perLocation"])) == dict(exp["locations"])
    assert m["medianDaysOpen"] == exp["median"]
    assert (m["eligibleCount"], m["quickCount"]) == (exp["eligible"], exp["quick"])
    assert m["shareWithin7"] == exp["share"]
    assert m["openCount"] == exp["open"]


def test_market_on_the_real_history_file():
    path = ROOT / "data" / "history.csv"
    exp = expected(path)
    out = subprocess.run(["node", str(ROOT / "tests" / "market_check.js"), str(path)],
                         capture_output=True, text=True, check=True)
    m = json.loads(out.stdout)
    assert m["openCount"] == exp["open"]
    assert dict(map(tuple, m["perEmployer"])) == dict(exp["employers"])
    assert m["medianDaysOpen"] == exp["median"]
    assert m["shareWithin7"] == exp["share"]
