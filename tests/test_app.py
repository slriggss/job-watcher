"""Small helpers shared by the pages (app.js), run in Node."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None and not os.environ.get("REQUIRE_NODE"),
                                reason="node not installed")


def out():
    r = subprocess.run(["node", str(ROOT / "tests" / "app_check.js")], capture_output=True, text=True,
                       encoding="utf-8", check=True)
    return json.loads(r.stdout)


def test_dates_read_as_month_and_day():
    assert out()["shortDate"] == ["Nov 5", "Oct 29", "", "abc"]


def test_the_in_role_tag_is_left_off_a_page_that_shows_only_role_postings():
    o = out()
    assert o["roleOnRolePage"] == "" and "in role" in o["roleElsewhere"]


def test_asset_manager_esg_postings_say_ESG_and_keep_the_reason_in_the_tooltip():
    tag = out()["esg"]
    assert ">ESG</span>" in tag and "matched on text: esg:3, stewardship:1" in tag and "risk/compliance" not in tag
    assert out()["plain"] == ""


def test_a_row_with_the_wrong_number_of_columns_is_dropped_by_the_csv_parser():
    assert out()["csv"] == 2  # the 1-column row is dropped (known: it is dropped silently)
