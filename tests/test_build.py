"""First-seen, last-seen, and removed logic, plus the rule that the history depends on raw files alone."""
import gzip
import json

from jobwatcher.build import build_history, build_status, load_raw, write_history

SRC_A = {"name": "a", "employer": "Alpha", "ats": "greenhouse", "token": "a"}
SRC_B = {"name": "b", "employer": "Beta", "ats": "greenhouse", "token": "b"}
SOURCES = [SRC_A, SRC_B]


def board(*ids, title="Analyst"):
    return {"jobs": [{"id": i, "title": f"{title} {i}", "absolute_url": f"https://x/{i}",
                      "location": {"name": "NYC"}} for i in ids]}


def by_id(rows):
    return {r["posting_id"]: r for r in rows}


def test_first_seen_last_seen_and_first_run():
    days = {"2026-10-01": {"a": board(1, 2)}, "2026-10-02": {"a": board(1, 2, 3)}}
    rows = by_id(build_history(days, SOURCES))
    assert rows["a:1"]["first_seen"] == "2026-10-01" and rows["a:1"]["last_seen"] == "2026-10-02"
    assert rows["a:1"]["first_run"] is True
    assert rows["a:3"]["first_seen"] == rows["a:3"]["last_seen"] == "2026-10-02"
    assert rows["a:3"]["first_run"] is False  # first listed after the source's first raw file
    assert all(r["status"] == "open" and r["removed_date"] == "" for r in rows.values())


def test_removed_when_source_has_a_file_and_no_longer_lists_it():
    days = {"2026-10-01": {"a": board(1, 2)}, "2026-10-02": {"a": board(1)}}
    rows = by_id(build_history(days, SOURCES))
    assert rows["a:2"]["status"] == "removed"
    assert rows["a:2"]["removed_date"] == "2026-10-02"
    assert rows["a:2"]["last_seen"] == "2026-10-01"
    assert rows["a:1"]["status"] == "open"


def test_failed_source_removes_nothing():
    # Source a has no raw file on the 2nd (it failed); its postings must stay open.
    days = {"2026-10-01": {"a": board(1), "b": board(9)}, "2026-10-02": {"b": board(9)}}
    rows = by_id(build_history(days, SOURCES))
    assert rows["a:1"]["status"] == "open" and rows["a:1"]["last_seen"] == "2026-10-01"
    assert rows["b:9"]["last_seen"] == "2026-10-02"


def test_relisted_posting_reopens_and_keeps_first_seen():
    days = {"2026-10-01": {"a": board(1, 2)}, "2026-10-02": {"a": board(1)},
            "2026-10-03": {"a": board(1, 2)}}
    r = by_id(build_history(days, SOURCES))["a:2"]
    assert r["status"] == "open"
    assert r["removed_date"] == ""
    assert r["first_seen"] == "2026-10-01"
    assert r["last_seen"] == "2026-10-03"


def test_first_run_is_per_source():
    days = {"2026-10-01": {"a": board(1)}, "2026-10-02": {"a": board(1), "b": board(5)}}
    rows = by_id(build_history(days, SOURCES))
    assert rows["a:1"]["first_run"] is True
    assert rows["b:5"]["first_run"] is True  # b's first raw file is on the 2nd


def test_in_role_follows_the_current_title_rule():
    days = {"2026-10-01": {"a": {"jobs": [
        {"id": 1, "title": "ESG Analyst", "absolute_url": "u", "location": {"name": ""}},
        {"id": 2, "title": "Backend Engineer", "absolute_url": "u", "location": {"name": ""}}]}}}
    rows = by_id(build_history(days, SOURCES))
    assert rows["a:1"]["in_role"] is True and rows["a:2"]["in_role"] is False


def test_rows_sorted_by_posting_id():
    days = {"2026-10-01": {"b": board(2, 10), "a": board(3)}}
    ids = [r["posting_id"] for r in build_history(days, SOURCES)]
    assert ids == sorted(ids)


def test_history_is_reproduced_from_raw_files(tmp_path):
    """Writing raw files, then building twice, gives the same file both times."""
    raw = tmp_path / "raw"
    for date, ids in [("2026-10-01", (1, 2)), ("2026-10-02", (2, 3))]:
        (raw / date).mkdir(parents=True)
        with gzip.open(raw / date / "a.json.gz", "wt") as f:
            json.dump(board(*ids), f)
    (raw / "2026-10-03").mkdir()  # a day with no raw file (only a results log) is not a day
    (raw / "2026-10-03" / "results.json").write_text("[]")
    outs = []
    for n in range(2):
        days = load_raw(raw)
        assert sorted(days) == ["2026-10-01", "2026-10-02"]
        write_history(build_history(days, SOURCES), tmp_path / f"h{n}.csv")
        outs.append((tmp_path / f"h{n}.csv").read_bytes())
    assert outs[0] == outs[1]
    assert b"removed" in outs[0]


def test_status_counts():
    days = {"2026-10-01": {"a": board(1, 2)}, "2026-10-02": {"a": board(2, 3)}}
    rows = build_history(days, SOURCES)
    st = build_status(rows, days, "2026-10-02T06:00:00Z",
                      [{"name": "a", "ok": True, "count": 2, "error": ""},
                       {"name": "b", "ok": False, "count": 0, "error": "boom"}])
    assert st["first_run_date"] == "2026-10-01"
    assert st["days_with_success"] == 2
    assert st["open"] == 2
    assert st["new_today"] == 1       # posting 3 (postings 1 and 2 are first-run)
    assert st["removed_today"] == 1   # posting 1
    assert st["sources"] == [{"name": "a", "ok": True, "count": 2}, {"name": "b", "ok": False, "count": 0}]
