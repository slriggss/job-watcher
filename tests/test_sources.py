"""Each source's conversion to the common columns."""
from jobwatcher.sources import (COLUMNS, normalize_ashby, normalize_greenhouse, normalize_lever,
                                normalize_smartrecruiters, normalize_workday)

GH = {"name": "stripe", "employer": "Stripe", "ats": "greenhouse", "token": "stripe"}
LV = {"name": "palantir", "employer": "Palantir", "ats": "lever", "token": "palantir"}
AS = {"name": "watershed", "employer": "Watershed", "ats": "ashby", "token": "watershed"}
SR = {"name": "experian", "employer": "Experian", "ats": "smartrecruiters", "token": "Experian"}
WD = {"name": "invesco", "employer": "Invesco", "ats": "workday", "tenant": "invesco",
      "wd": "wd1", "site": "IVZ"}


def test_greenhouse():
    raw = {"jobs": [{"id": 123, "title": " ESG Analyst ", "absolute_url": "https://x/123",
                     "location": {"name": "New York"}}]}
    (row,) = normalize_greenhouse(GH, raw)
    assert list(row) == COLUMNS
    assert row["posting_id"] == "stripe:123"
    assert row["source_id"] == "123"
    assert row["employer"] == "Stripe"
    assert row["title"] == "ESG Analyst"
    assert row["location"] == "New York"
    assert row["url"] == "https://x/123"
    assert row["department"] == "" and row["posted_date"] == ""


def test_greenhouse_missing_location():
    (row,) = normalize_greenhouse(GH, {"jobs": [{"id": 1, "title": "T", "absolute_url": "u", "location": None}]})
    assert row["location"] == ""


def test_lever():
    raw = [{"id": "abc-1", "text": "Analyst", "hostedUrl": "https://jobs.lever.co/palantir/abc-1",
            "createdAt": 1761696000000, "categories": {"location": "Denver", "department": "Finance"}}]
    (row,) = normalize_lever(LV, raw)
    assert row["posting_id"] == "palantir:abc-1"
    assert row["title"] == "Analyst"
    assert row["location"] == "Denver"
    assert row["department"] == "Finance"
    assert row["posted_date"] == "2025-10-29"  # epoch milliseconds -> UTC date
    assert row["url"] == "https://jobs.lever.co/palantir/abc-1"


def test_lever_without_categories_or_date():
    (row,) = normalize_lever(LV, [{"id": "z", "text": "T", "hostedUrl": "u"}])
    assert row["location"] == "" and row["department"] == "" and row["posted_date"] == ""


def test_ashby():
    raw = {"jobs": [{"id": "u-1", "title": "Sustainability data advisor", "jobUrl": "https://jobs.ashbyhq.com/w/u-1",
                     "location": "Remote", "department": "Services", "publishedAt": "2026-10-01T12:30:00.000+00:00"}]}
    (row,) = normalize_ashby(AS, raw)
    assert row["posting_id"] == "watershed:u-1"
    assert row["department"] == "Services"
    assert row["posted_date"] == "2026-10-01"
    assert row["location"] == "Remote"


def test_smartrecruiters():
    raw = {"totalFound": 1, "content": [{
        "id": "744", "name": "Credit Analyst", "releasedDate": "2026-09-15T08:00:00.000Z",
        "department": {"label": "Risk"},
        "location": {"city": "Costa Mesa", "region": "CA", "country": "us"}}]}
    (row,) = normalize_smartrecruiters(SR, raw)
    assert row["posting_id"] == "experian:744"
    assert row["location"] == "Costa Mesa, CA, US"
    assert row["department"] == "Risk"
    assert row["posted_date"] == "2026-09-15"
    assert row["url"] == "https://jobs.smartrecruiters.com/Experian/744"


def test_workday():
    raw = {"total": 2, "jobPostings": [
        {"title": "Analyst", "externalPath": "/job/London-London/Analyst_R-15786",
         "locationsText": "London", "postedOn": "Posted Today", "bulletFields": ["R-15786"]},
        {"title": "Analyst (dup)", "externalPath": "/job/Elsewhere/Analyst_R-15786",
         "locationsText": "Elsewhere", "bulletFields": ["R-15786"]}]}
    rows = normalize_workday(WD, raw)
    assert len(rows) == 1  # a requisition id listed twice is one posting
    row = rows[0]
    assert row["posting_id"] == "invesco:R-15786"
    assert row["url"] == "https://invesco.wd1.myworkdayjobs.com/IVZ/job/London-London/Analyst_R-15786"
    assert row["location"] == "London"
    assert row["posted_date"] == ""  # Workday only gives relative text such as "Posted Today"


def test_every_normalizer_returns_the_common_columns():
    cases = [(normalize_greenhouse, GH, {"jobs": [{"id": 1}]}),
             (normalize_lever, LV, [{"id": "a"}]),
             (normalize_ashby, AS, {"jobs": [{"id": "a"}]}),
             (normalize_smartrecruiters, SR, {"content": [{"id": "a"}]}),
             (normalize_workday, WD, {"jobPostings": [{"externalPath": "/job/x_R-1"}]})]
    for fn, src, raw in cases:
        assert list(fn(src, raw)[0]) == COLUMNS
