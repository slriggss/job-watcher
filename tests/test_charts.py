"""The Market charts are drawn at the card's real width with readable, uncut text (run in Node with a stub card)."""
import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None and not os.environ.get("REQUIRE_NODE"),
                                reason="node not installed")


def draw(width):
    out = subprocess.run(["node", str(ROOT / "tests" / "charts_check.js"), str(width)],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


def svg_of(html):
    return ET.fromstring(html.replace("&", "&amp;").replace("&amp;amp;", "&amp;"))


@pytest.mark.parametrize("card_width", [390, 820, 1366])
def test_every_chart_is_drawn_at_the_cards_width(card_width):
    inner = max(280, card_width - 24)
    for name, html in draw(card_width).items():
        svg = svg_of(html)
        assert svg.get("width") == str(inner), name  # real pixels, not a fixed 720 scaled down
        assert svg.get("viewBox").split()[2] == str(inner), name


def test_employer_names_are_never_cut_on_a_phone_or_a_desktop():
    for w in (390, 1366):
        text = " ".join(t.text or "" for t in svg_of(draw(w)["hbar"]).iter("text"))
        assert "Ameriprise (Columbia Threadneedle)" in text and "…" not in text, w


def test_phone_layout_puts_the_name_above_the_bar():
    svg = svg_of(draw(390)["hbar"])
    first = svg.find(".//g[@class='col h']")
    label, bar = first.findall("text")[0], first.find("rect[@class='bar']")
    assert float(label.get("x")) == 0 and float(bar.get("x")) == 0 and float(label.get("y")) < float(bar.get("y"))


def test_dates_read_as_month_and_day_and_stay_flat():
    html = draw(1366)["bar"]
    assert "Nov 5" in html and "Oct 29" in html and "rotate" not in html


def test_axis_maxima_are_round_and_close_to_the_data():
    ticks = [int(t) for t in re.findall(r"text-anchor=\"end\">(\d+)</text>", draw(1366)["bar"])]
    assert ticks == [0, 5, 10, 15, 20]  # not 0, 7, 15, 22, 30
