"""Reading posting text: the term scan, the Workday detail link, caching, back-off, and the text routes into am_esg."""
import requests

from jobwatcher.build import build_history, load_enrich
from jobwatcher.enrich import candidates, description_url, enrich, scan
from jobwatcher.sources import SOURCES
from jobwatcher.titlerule import esg_via

BLACKROCK = next(s for s in SOURCES if s["name"] == "blackrock")


def row(pid, source="blackrock", title="Analyst", status="open", etype="asset manager", first_seen="2026-10-01"):
    return {"posting_id": pid, "source": source, "title": title, "status": status, "employer_type": etype,
            "first_seen": first_seen, "url": f"https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional/job/NY/X_{pid}"}


def test_scan_counts_strong_terms():
    n, terms = scan("Our ESG team leads stewardship. ESG integration and proxy voting. Net-zero and SFDR work.")
    assert n == 6
    assert terms.startswith("esg:2;")
    assert "stewardship:1" in terms and "net-zero:1" in terms and "sfdr:1" in terms


def test_scan_ignores_generic_words():
    assert scan("Join a growing, sustainable business with strong governance and great benefits.") == (0, "")
    assert scan("") == (0, "") and scan(None) == (0, "")


def test_description_url_uses_the_workday_detail_endpoint():
    url = "https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional/job/NY-New-York/Analyst_R123"
    assert description_url(BLACKROCK, url) == (
        "https://blackrock.wd1.myworkdayjobs.com/wday/cxs/blackrock/BlackRock_Professional/job/NY-New-York/Analyst_R123")


def test_candidates_are_open_asset_manager_workday_postings_not_yet_read():
    rows = [row("blackrock:1"), row("blackrock:2", status="removed"), row("stripe:3", source="stripe", etype="fintech"),
            row("blackrock:4"), row("blackrock:5", first_seen="2026-10-05")]
    got = [r["posting_id"] for r in candidates(rows, {"blackrock:4": {"strong": 0, "terms": ""}})]
    assert got == ["blackrock:5", "blackrock:1"]  # newest first; removed, non-asset-manager and cached ones left out


def test_enrich_writes_a_cache_once_and_skips_failures(tmp_path):
    path = tmp_path / "enrich.csv"
    rows = [row("blackrock:1"), row("blackrock:2")]

    def fetch(src, url):
        if url.endswith("_blackrock:2"):
            raise RuntimeError("boom")
        return "ESG stewardship and ESG"

    assert enrich(rows, path=path, fetch=fetch, pause=0, workers=1, today="2026-11-03") == (1, 1)
    cache = load_enrich(path)
    assert cache == {"blackrock:1": {"strong": 3, "terms": "esg:2;stewardship:1"}}  # the failure is not cached
    assert enrich(rows, path=path, fetch=lambda s, u: "none", pause=0, workers=1) == (1, 0)  # only the failed one retried


def test_enrich_stops_asking_a_source_that_says_forbidden(tmp_path):
    calls = []

    def fetch(src, url):
        calls.append(url)
        err = requests.HTTPError("403")
        err.response = type("R", (), {"status_code": 403})()
        raise err

    rows = [row(f"blackrock:{i}") for i in range(10)]
    done, failed = enrich(rows, path=tmp_path / "e.csv", fetch=fetch, pause=0, workers=1)
    assert done == 0 and len(calls) == 1  # one refusal and it leaves that employer alone
    assert not (tmp_path / "e.csv").exists()


def test_esg_via_routes():
    # a title match wins; text only counts at asset managers; risk and compliance roles need less text
    assert esg_via("Stewardship Analyst", "asset manager") == "title"
    assert esg_via("Senior Analyst", "asset manager", strong=3) == "text"
    assert esg_via("Senior Analyst", "asset manager", strong=2) == ""
    assert esg_via("Compliance Officer", "asset manager", strong=2) == "risk/compliance text"
    assert esg_via("Compliance Officer", "asset manager", strong=1) == ""
    assert esg_via("Software Engineer", "asset manager", strong=1) == ""
    assert esg_via("Compliance Officer", "bank", strong=9) == ""
    assert esg_via("Senior Analyst", "fintech", strong=9) == ""


def test_build_history_applies_the_text_counts():
    board = {"jobs": [{"id": i, "title": t, "absolute_url": f"https://x/{i}", "location": {"name": "NYC"}}
                      for i, t in [(1, "Senior Analyst"), (2, "Risk Manager"), (3, "Software Engineer")]]}
    src = {"name": "blackrock", "employer": "BlackRock", "ats": "greenhouse", "token": "b"}
    cache = {"blackrock:1": {"strong": 4, "terms": "esg:4"}, "blackrock:2": {"strong": 2, "terms": "climate risk:2"},
             "blackrock:3": {"strong": 1, "terms": "esg:1"}}
    rows = {r["posting_id"]: r for r in build_history({"2026-10-01": {"blackrock": board}}, [src], enrich=cache)}
    assert (rows["blackrock:1"]["am_esg"], rows["blackrock:1"]["esg_via"]) == (True, "text")
    assert (rows["blackrock:2"]["am_esg"], rows["blackrock:2"]["esg_via"]) == (True, "risk/compliance text")
    assert rows["blackrock:3"]["am_esg"] is False
    assert rows["blackrock:1"]["esg_terms"] == "esg:4"


def test_a_repeated_term_pattern_is_boilerplate_and_ignored():
    src = {"name": "blackrock", "employer": "BlackRock", "ats": "greenhouse", "token": "b"}
    board = {"jobs": [{"id": i, "title": f"HR Adviser {i}", "absolute_url": f"https://x/{i}", "location": {"name": "NYC"}}
                      for i in range(1, 5)]}
    same = {"strong": 4, "terms": "esg:3;responsible investment:1"}
    cache = {f"blackrock:{i}": dict(same) for i in (1, 2, 3)}
    cache["blackrock:4"] = {"strong": 4, "terms": "esg:4"}  # a different pattern: about this role
    rows = {r["posting_id"]: r for r in build_history({"2026-10-01": {"blackrock": board}}, [src], enrich=cache)}
    assert [rows[f"blackrock:{i}"]["am_esg"] for i in (1, 2, 3)] == [False, False, False]
    assert rows["blackrock:4"]["am_esg"] is True


def test_risk_and_compliance_roles_are_read_first():
    rows = [row("blackrock:1", title="Software Engineer", first_seen="2026-10-09"),
            row("blackrock:2", title="Compliance Officer", first_seen="2026-10-01")]
    assert [r["posting_id"] for r in candidates(rows, {})] == ["blackrock:2", "blackrock:1"]
