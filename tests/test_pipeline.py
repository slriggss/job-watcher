"""The daily run's rules: safe reruns, short pulls, the issue text, and which issues get closed."""
import gzip
import json

import pytest

from jobwatcher import pipeline
from jobwatcher.build import build_history
from jobwatcher.sources import normalize_greenhouse

SRC_A = {"name": "a", "employer": "Alpha", "ats": "greenhouse", "token": "a"}
SRC_B = {"name": "b", "employer": "Beta", "ats": "greenhouse", "token": "b"}
DAY = "2026-11-06"


def board(*ids):
    return {"jobs": [{"id": i, "title": f"Analyst {i}", "absolute_url": f"https://x/{i}",
                      "location": {"name": "NYC"}} for i in ids]}


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "DATA", tmp_path)
    return tmp_path


def fake_fetch(monkeypatch, boards):
    """boards: source name -> raw board, or an Exception to raise."""
    def fetch(src):
        out = boards[src["name"]]
        if isinstance(out, Exception):
            raise out
        return out
    monkeypatch.setitem(pipeline.FETCH, "greenhouse", fetch)


def read_names(day_dir):
    return sorted(p.name for p in day_dir.iterdir())


def test_rerun_where_every_source_fails_keeps_the_day(data, monkeypatch):
    fake_fetch(monkeypatch, {"a": board(1), "b": board(2)})
    pipeline.fetch_all(DAY, [SRC_A, SRC_B])
    before = read_names(data / "raw" / DAY)
    fake_fetch(monkeypatch, {"a": OSError("offline"), "b": OSError("offline")})
    results = pipeline.fetch_all(DAY, [SRC_A, SRC_B])
    assert not any(r["ok"] for r in results)
    assert set(before) <= set(read_names(data / "raw" / DAY))  # nothing was deleted
    assert (data / "raw" / DAY / "results.failed.json").exists()  # and the failures are on record
    assert json.loads((data / "raw" / DAY / "results.json").read_text())[0]["ok"] is True
    assert not list((data / "raw").glob(".tmp-*"))


def test_rerun_keeps_the_earlier_file_of_a_source_that_now_fails(data, monkeypatch):
    fake_fetch(monkeypatch, {"a": board(1), "b": board(2, 3)})
    pipeline.fetch_all(DAY, [SRC_A, SRC_B])
    fake_fetch(monkeypatch, {"a": board(1, 4), "b": OSError("boom")})
    results = {r["name"]: r for r in pipeline.fetch_all(DAY, [SRC_A, SRC_B])}
    assert results["b"]["ok"] is False and results["b"]["kept_earlier"] is True and results["b"]["count"] == 2
    kept = json.loads(gzip.decompress((data / "raw" / DAY / "b.json.gz").read_bytes()))
    assert [j["id"] for j in kept["jobs"]] == [2, 3]
    fresh = json.loads(gzip.decompress((data / "raw" / DAY / "a.json.gz").read_bytes()))
    assert [j["id"] for j in fresh["jobs"]] == [1, 4]


def test_first_run_of_a_day_with_no_success_leaves_no_raw_files(data, monkeypatch):
    fake_fetch(monkeypatch, {"a": OSError("offline"), "b": OSError("offline")})
    pipeline.fetch_all(DAY, [SRC_A, SRC_B])
    assert not list((data / "raw" / DAY).glob("*.json.gz"))
    assert not pipeline.day_is_done(DAY)


def test_day_is_done_after_a_successful_run(data, monkeypatch):
    fake_fetch(monkeypatch, {"a": board(1), "b": OSError("x")})
    pipeline.fetch_all(DAY, [SRC_A, SRC_B])
    assert pipeline.day_is_done(DAY)


def test_a_short_pull_is_a_failed_pull(monkeypatch):
    wd = {"name": "w", "employer": "W", "ats": "workday", "tenant": "w", "wd": "wd1", "site": "S"}
    page = lambda n: {"total": 100, "jobPostings": [{"title": f"t{i}", "externalPath": f"/job/x_R-{i}"} for i in range(n)]}
    monkeypatch.setitem(pipeline.FETCH, "workday", lambda src: page(60))
    _, raw, result = pipeline.fetch_source(wd)
    assert raw is None and result["ok"] is False and "60 postings against a reported total of 100" in result["error"]
    monkeypatch.setitem(pipeline.FETCH, "workday", lambda src: page(97))  # a few duplicates or shifts are tolerated
    assert pipeline.fetch_source(wd)[2]["ok"] is True


def test_source_health_flags_a_collapse_and_remembers_last_success(data):
    for day, count in (("2026-11-04", 9), ("2026-11-05", 9)):
        (data / "raw" / day).mkdir(parents=True)
        (data / "raw" / day / "results.json").write_text(json.dumps(
            [{"name": "patch", "ok": True, "count": count, "error": ""},
             {"name": "gone", "ok": True, "count": 20, "error": ""}]))
    out = pipeline.source_health(DAY, [{"name": "patch", "ok": True, "count": 1, "error": ""},
                                       {"name": "gone", "ok": False, "count": 0, "error": "x"}])
    patch, gone = out
    assert patch["suspect"] is True and patch["last_ok"] == DAY
    assert gone["suspect"] is False and gone["last_ok"] == "2026-11-05"


# ---- the issue -------------------------------------------------------------------------------
def row(i, employer="Alpha", title=None, in_role=False, **kw):
    return {"title": title or f"Analyst {i}", "url": f"https://x/{i}", "employer": employer, "location": "NYC",
            "in_role": in_role, "first_seen": DAY, "first_run": False, "removed_date": "", **kw}


def test_issue_lists_every_posting_even_when_it_needs_comments():
    rows = [row(i, employer=f"E{i % 7}") for i in range(300)]
    rows += [row(1000 + i, removed_date=DAY, first_seen="2026-11-01") for i in range(50)]
    parts = pipeline.issue_parts(rows, DAY, [], limit=3000)
    assert len(parts) > 1 and all(p.startswith(pipeline.OVERFLOW_MARK) for p in parts[1:])
    text = "\n".join(parts)
    assert sum(1 for i in range(300) if f"(https://x/{i})" in text) == 300
    assert sum(1 for i in range(50) if f"(https://x/{1000 + i})" in text) == 50
    assert "see data/history.csv" not in text
    assert all(len(p) < 3600 for p in parts)


def test_issue_groups_by_employer_and_puts_role_postings_first():
    rows = [row(1, employer="Zed", title="ESG Analyst", in_role=True), row(2, employer="Alpha"), row(3, employer="Zed")]
    body = pipeline.issue_parts(rows, DAY, [])[0]
    assert body.index("**Zed** (2)") < body.index("**Alpha** (1)")
    assert body.index("ESG Analyst") < body.index("Analyst 3")
    assert "Removed postings (0)" in body and "None." in body


def test_issue_neutralizes_markup_mentions_and_cross_references():
    rows = [row(1, title="Lead Analyst #4 @octocat [x](http://evil)"),
            {**row(2), "url": "javascript:alert(1)"}]
    body = pipeline.issue_parts(rows, DAY, [])[0]
    assert "#4" not in body and "@octocat" not in body and "[x](http://evil)" not in body
    assert "javascript:" not in body


def test_failed_sources_are_named_in_the_issue():
    body = pipeline.issue_parts([], DAY, [{"name": "blueowl", "ok": False}])[0]
    assert "Sources that failed today: blueowl." in body


def test_only_labelled_open_run_issues_are_closed():
    listing = [{"number": 1, "title": "2026-11-05", "state": "OPEN", "labels": ["daily-run"]},
               {"number": 2, "title": "Question from a classmate", "state": "OPEN", "labels": []},
               {"number": 3, "title": DAY, "state": "OPEN", "labels": ["daily-run"]},
               {"number": 4, "title": "2026-11-04", "state": "CLOSED", "labels": ["daily-run"]}]
    assert pipeline.issues_to_close(listing, DAY) == [1]


def test_update_issue_replaces_overflow_comments_on_a_rerun():
    calls = []

    def run(*args, body=None):
        calls.append(args)
        out = {"issue list": [{"number": 7, "title": DAY, "state": "OPEN", "labels": [{"name": "daily-run"}]}],
               "issue view": {"comments": [
                   {"body": pipeline.OVERFLOW_MARK + " old", "url": "https://github.com/o/r/issues/7#issuecomment-555"},
                   {"body": "a human reply", "url": "https://github.com/o/r/issues/7#issuecomment-556"}]}}
        return type("R", (), {"stdout": json.dumps(out.get(" ".join(args[:2]), {}))})()

    pipeline.update_issue(DAY, ["body", "overflow one"], run=run)
    flat = [" ".join(c) for c in calls]
    assert any(c.endswith("issues/comments/555") for c in flat)
    assert not any("556" in c for c in flat)
    assert "issue comment 7" in flat and "issue edit 7" in flat


# ---- history fields --------------------------------------------------------------------------
def test_a_blank_relisting_keeps_the_earlier_title_and_location():
    days = {"2026-11-05": {"a": board(1)},
            "2026-11-06": {"a": {"jobs": [{"id": 1, "title": "", "absolute_url": "https://x/1", "location": {"name": ""}}]}}}
    (r,) = build_history(days, [SRC_A])
    assert r["title"] == "Analyst 1" and r["location"] == "NYC"


def test_titles_have_whitespace_collapsed():
    raw = {"jobs": [{"id": 1, "title": " Operation Risk  Management   Associate ", "absolute_url": "u"}]}
    assert normalize_greenhouse(SRC_A, raw)[0]["title"] == "Operation Risk Management Associate"


def test_greenhouse_posted_date_is_the_utc_date():
    raw = {"jobs": [{"id": 1, "title": "t", "absolute_url": "u", "first_published": "2026-10-10T21:56:00-04:00"},
                    {"id": 2, "title": "t", "absolute_url": "u", "first_published": "2026-10-10T08:00:00-04:00"},
                    {"id": 3, "title": "t", "absolute_url": "u"}]}
    dates = [r["posted_date"] for r in normalize_greenhouse(SRC_A, raw)]
    assert dates == ["2026-10-11", "2026-10-10", ""]
