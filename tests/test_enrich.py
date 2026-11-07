"""Reading posting text: the term scan, the Workday detail link, caching, back-off, and the text routes into am_esg."""
import requests

from jobwatcher.build import build_history, detail_ids, load_details
from jobwatcher.enrich import candidates, description_url, enrich, save_detail, scan
from jobwatcher.sources import SOURCES
from jobwatcher.titlerule import esg_via

BLACKROCK = next(s for s in SOURCES if s["name"] == "blackrock")


def row(pid, source="blackrock", title="Analyst", status="open", etype="asset manager", first_seen="2026-10-01",
        location="New York, NY"):
    sid = pid.split(":")[1]
    return {"posting_id": pid, "source": source, "source_id": sid, "title": title, "status": status,
            "employer_type": etype, "first_seen": first_seen, "location": location,
            "url": f"https://blackrock.wd1.myworkdayjobs.com/BlackRock_Professional/job/NY/X_{sid}"}


def detail(text="", location="", more=(), start=""):
    return {"jobPostingInfo": {"jobDescription": f"<p>{text}</p>", "location": location,
                               "additionalLocations": list(more), "startDate": start}}


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


def test_candidates_are_open_workday_postings_that_need_text_or_locations_and_have_no_file():
    rows = [row("blackrock:1"), row("blackrock:2", status="removed"), row("stripe:3", source="stripe", etype="fintech"),
            row("blackrock:4"), row("blackrock:5", first_seen="2026-10-05"),
            row("statestreet:6", source="statestreet", etype="bank", location="2 Locations"),
            row("statestreet:7", source="statestreet", etype="bank")]
    got = [r["posting_id"] for r in candidates(rows, {"blackrock:4"})]
    # removed, fintech, an ordinary bank posting and ones that already have a file are left out
    assert set(got) == {"blackrock:5", "blackrock:1", "statestreet:6"}


def test_postings_read_before_descriptions_were_saved_come_first():
    rows = [row("blackrock:1", first_seen="2026-10-09"), row("blackrock:2", first_seen="2026-10-01")]
    assert [r["posting_id"] for r in candidates(rows, set(), legacy={"blackrock:2"})] == ["blackrock:2", "blackrock:1"]


def test_enrich_saves_each_description_once_and_skips_failures(tmp_path):
    rows = [row("blackrock:1"), row("blackrock:2")]

    def fetch(src, url):
        if url.endswith("_2"):
            raise RuntimeError("boom")
        return detail("ESG stewardship and ESG")

    out = enrich(rows, fetch=fetch, pause=0, workers=1, root=tmp_path, today="2026-11-03", legacy_path=tmp_path / "x.csv")
    assert out[:3] == (1, 1, []) and out[3] == ["blackrock:1"]
    assert load_details(tmp_path)["blackrock:1"]["strong"] == 3 and detail_ids(tmp_path) == {"blackrock:1"}
    again = enrich(rows, fetch=lambda s, u: detail("none"), pause=0, workers=1, root=tmp_path, today="2026-11-03",
                   legacy_path=tmp_path / "x.csv")
    assert again[:2] == (1, 0)  # only the failed one is fetched again


def test_enrich_stops_asking_a_source_that_says_forbidden_and_remembers_it(tmp_path):
    calls = []

    def fetch(src, url):
        calls.append(url)
        err = requests.HTTPError("403")
        err.response = type("R", (), {"status_code": 403})()
        raise err

    rows = [row(f"blackrock:{i}") for i in range(10)]
    kw = dict(fetch=fetch, pause=0, workers=1, root=tmp_path, legacy_path=tmp_path / "x.csv")
    done, failed, blocked, _ = enrich(rows, today="2026-11-03", **kw)
    assert done == 0 and len(calls) == 1 and blocked == ["blackrock"]  # one refusal and it leaves that employer alone
    enrich(rows, today="2026-11-05", **kw)
    assert len(calls) == 1  # still resting two days later, and it did not use up any of the run's slots
    enrich(rows, today="2026-11-11", **kw)
    assert len(calls) == 2  # asked again after the rest period


def test_build_history_reads_term_counts_locations_and_start_date_from_saved_files(tmp_path):
    save_detail("blackrock", "1", detail("ESG ESG ESG stewardship", "Charlotte, NC",
                                         ["5335 Ballantyne Commons Pkwy, Charlotte, NC", "Huntersville, NC"], "2026-10-12"), tmp_path)
    src = {"name": "blackrock", "employer": "BlackRock", "ats": "greenhouse", "token": "b"}
    board = {"jobs": [{"id": 1, "title": "Senior Analyst", "absolute_url": "https://x/1", "location": {"name": "3 Locations"}},
                      {"id": 2, "title": "Senior Analyst", "absolute_url": "https://x/2", "location": {"name": "3 Locations"}}]}
    rows = {r["posting_id"]: r for r in
            build_history({"2026-10-01": {"blackrock": board}}, [src], enrich=load_details(tmp_path))}
    r1, r2 = rows["blackrock:1"], rows["blackrock:2"]
    assert (r1["text_read"], r1["am_esg"], r1["esg_via"], r1["esg_terms"]) == (True, True, "text", "esg:3;stewardship:1")
    assert (r1["location_norm"], r1["locations_all"], r1["posted_date"]) == ("Charlotte, NC", "Charlotte, NC;Huntersville, NC", "2026-10-12")
    assert r1["location"] == "3 Locations"  # the original text is kept
    assert (r2["text_read"], r2["location_norm"], r2["am_esg"]) == (False, "", False)  # unread and unresolved are distinguishable


def test_the_history_rebuilds_identically_from_the_raw_folder_alone(tmp_path):
    save_detail("blackrock", "1", detail("ESG ESG ESG"), tmp_path)
    src = {"name": "blackrock", "employer": "BlackRock", "ats": "greenhouse", "token": "b"}
    board = {"jobs": [{"id": 1, "title": "Senior Analyst", "absolute_url": "https://x/1", "location": {"name": "NYC"}}]}
    days = {"2026-10-01": {"blackrock": board}}
    first = build_history(days, [src], enrich=load_details(tmp_path))
    # a change to the term list reaches the posting because the text is kept, not just its count
    assert first[0]["esg_terms"] == "esg:3"
    assert build_history(days, [src], enrich=load_details(tmp_path)) == first


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
    assert [r["posting_id"] for r in candidates(rows, set())] == ["blackrock:2", "blackrock:1"]
