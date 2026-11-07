"""The daily fact follows the calendar: a fact on its date, the nearest dated fact within a week (labelled with its
real date), and an undated fact only when nothing is that close."""
import json
import os
import re
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None and not os.environ.get("REQUIRE_NODE"),
                                reason="node not installed")


def run(*dates):
    r = subprocess.run(["node", str(ROOT / "tests" / "facts_check.js"), *dates], capture_output=True, text=True,
                       encoding="utf-8", check=True)
    return json.loads(r.stdout)


def test_a_dated_fact_shows_on_its_date_every_year():
    out = run("2026-11-10", "2027-11-10", "2026-11-07", "2026-12-10")
    assert "windshield wiper" in out["picks"][0]["text"] and out["picks"][0]["label"] == "On this day · 1903"
    assert out["picks"][1] == out["picks"][0]
    assert "Marie Curie" in out["picks"][2]["text"]
    assert "Ada Lovelace" in out["picks"][3]["text"]


def test_two_facts_on_one_date_alternate_by_year():
    out = run("2026-12-28", "2027-12-28")
    assert {p["text"][:10] for p in out["picks"]} == {"Josephine ", "Muriel Sie"}


def test_a_day_without_its_own_fact_shows_the_nearest_dated_one_with_its_real_date():
    out = run("2026-11-13", "2026-11-08", "2026-12-30", "2026-01-03")
    assert out["picks"][0]["label"] == "Nov 10, 1903 \u00b7 in 3 days" or out["picks"][0]["label"] == "Nov 10, 1903 \u00b7 3 days ago"
    assert out["picks"][1]["label"] in ("Nov 7, 1867 \u00b7 yesterday", "Nov 9, 1914 \u00b7 tomorrow")
    assert out["picks"][2]["label"].startswith("Dec 28")  # two days earlier than Dec 30
    assert out["picks"][3]["label"].startswith("Jan 1, 2012")  # across New Year, nearest is Jan 1


def test_every_day_from_november_7_through_january_31_is_within_a_week_of_a_dated_fact():
    start = date(2026, 11, 7)
    days = [(start + timedelta(days=i)).isoformat() for i in range((date(2027, 1, 31) - start).days + 1)]
    picks = run(*days)["picks"]
    assert len(picks) == 86
    assert not [d for d, p in zip(days, picks) if p["label"].startswith("Women in business")]


def test_an_undated_fact_fills_in_only_when_nothing_dated_is_near():
    out = run("2026-06-20", "2026-06-21")
    assert all(p["label"].startswith("Women in business") for p in out["picks"])
    assert out["picks"][0]["text"] != out["picks"][1]["text"]


def test_the_list_is_well_formed():
    facts = run()["facts"]
    texts = [f["text"] for f in facts]
    assert len(set(texts)) == len(texts) and all(len(t) > 40 for t in texts)
    for f in facts:
        year = f["year"]
        assert isinstance(year, str) or 1800 < year <= 2026
        if "on" in f:
            assert re.fullmatch(r"\d\d-\d\d", f["on"])
            date(2024, int(f["on"][:2]), int(f["on"][3:]))  # a real calendar date (2024 is a leap year)
    assert len([f for f in facts if "on" in f]) >= 20 and len([f for f in facts if "on" not in f]) >= 20
