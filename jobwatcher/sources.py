"""Every source the tool watches: how to fetch it and how to convert it to the common columns."""
import re
import time
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COLUMNS = ["posting_id", "source", "source_id", "employer", "title", "location",
           "department", "posted_date", "url"]
HEADERS = {"User-Agent": "job-watcher/1.0 (student project; daily job board snapshot)",
           "Accept": "application/json"}
TIMEOUT = 30

# One session for every fetch: connections are reused, and a timeout, 429 or 5xx is retried with backoff
# (Retry honours a Retry-After header). POST is retried too: Workday's list endpoint is a read-only POST.
SESSION = requests.Session()
SESSION.mount("https://", HTTPAdapter(max_retries=Retry(
    total=4, backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=None, respect_retry_after_header=True)))

# A paged board that returns fewer than this share of its own reported total is treated as a failed pull.
MIN_SHARE_OF_TOTAL = 0.95


def _clean(text):
    """Trim and collapse runs of whitespace, so search and duplicate checks behave."""
    return " ".join((text or "").split())


def _row(src, source_id, title, url, location="", department="", posted_date=""):
    source_id = str(source_id)
    return {"posting_id": f"{src['name']}:{source_id}", "source": src["name"],
            "source_id": source_id, "employer": src["employer"], "title": _clean(title),
            "location": _clean(location), "department": _clean(department),
            "posted_date": posted_date or "", "url": url or ""}


def _ms_date(ms):
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _iso_date(s):
    return (s or "")[:10]


def _utc_date(s):
    """An ISO timestamp with an offset (2026-10-10T21:56:00-04:00) -> its UTC calendar date."""
    if not s:
        return ""
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return _iso_date(s)
    if d.tzinfo is None:
        return d.strftime("%Y-%m-%d")
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d")


# ---- Greenhouse -------------------------------------------------------------------------
def fetch_greenhouse(src):
    r = SESSION.get(f"https://boards-api.greenhouse.io/v1/boards/{src['token']}/jobs",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def normalize_greenhouse(src, raw):
    return [_row(src, j["id"], j.get("title"), j.get("absolute_url"),
                 (j.get("location") or {}).get("name", ""), "", _utc_date(j.get("first_published")))
            for j in raw["jobs"]]


# ---- Lever ------------------------------------------------------------------------------
def fetch_lever(src):
    r = SESSION.get(f"https://api.lever.co/v0/postings/{src['token']}?mode=json",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def normalize_lever(src, raw):
    out = []
    for j in raw:
        cat = j.get("categories") or {}
        out.append(_row(src, j["id"], j.get("text"), j.get("hostedUrl"),
                        cat.get("location", ""), cat.get("department", ""),
                        _ms_date(j.get("createdAt"))))
    return out


# ---- Ashby ------------------------------------------------------------------------------
def fetch_ashby(src):
    r = SESSION.get(f"https://api.ashbyhq.com/posting-api/job-board/{src['token']}",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def normalize_ashby(src, raw):
    return [_row(src, j["id"], j.get("title"), j.get("jobUrl"), j.get("location", ""),
                 j.get("department", ""), _iso_date(j.get("publishedAt")))
            for j in raw["jobs"]]


# ---- SmartRecruiters --------------------------------------------------------------------
def fetch_smartrecruiters(src):
    content, offset = [], 0
    while True:
        r = SESSION.get(f"https://api.smartrecruiters.com/v1/companies/{src['token']}/postings",
                         params={"limit": 100, "offset": offset}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        page = r.json()
        content += page["content"]
        offset += 100
        if offset >= page["totalFound"] or not page["content"]:
            # an empty page before the total is reached is left for fetch_source's completeness check
            return {"totalFound": page["totalFound"], "content": content}


def normalize_smartrecruiters(src, raw):
    out = []
    for j in raw["content"]:
        loc = j.get("location") or {}
        place = ", ".join(p for p in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if p)
        out.append(_row(src, j["id"], j.get("name"),
                        f"https://jobs.smartrecruiters.com/{src['token']}/{j['id']}", place,
                        (j.get("department") or {}).get("label", ""), _iso_date(j.get("releasedDate"))))
    return out


# ---- Workday ----------------------------------------------------------------------------
def workday_base(src):
    return f"https://{src['tenant']}.{src['wd']}.myworkdayjobs.com"


def fetch_workday(src):
    url = f"{workday_base(src)}/wday/cxs/{src['tenant']}/{src['site']}/jobs"
    postings, offset, total, empty_retried = [], 0, None, False
    while total is None or offset < total:
        r = SESSION.post(url, json={"limit": 20, "offset": offset, "searchText": src.get("search", "")},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        page = r.json()
        if total is None:
            total = page["total"]  # Workday reports the total only on the first page
        if not page["jobPostings"]:
            if empty_retried:  # an empty page twice in a row: stop; fetch_source compares with the total
                break
            empty_retried = True
            time.sleep(1)
            continue
        empty_retried = False
        postings += page["jobPostings"]
        offset += 20
        time.sleep(0.1)
    return {"total": total, "jobPostings": postings}


def normalize_workday(src, raw):
    out, seen = [], set()
    for j in raw["jobPostings"]:
        path = j.get("externalPath")
        if not path:  # Workday sometimes lists a stub with only a requisition id: no title, no link
            continue
        m = re.search(r"_([^_/]+)$", path)  # the requisition id closes the path: ..._R-12345
        sid = m.group(1) if m else path
        if sid in seen:
            continue
        seen.add(sid)
        out.append(_row(src, sid, j.get("title"), f"{workday_base(src)}/{src['site']}{path}",
                        j.get("locationsText", "")))
    return out


# ---- Oracle Recruiting Cloud (JPMorgan) ---------------------------------------------------
def fetch_oracle(src):
    url = f"https://{src['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    if re.search(r"[,;=]", src.get("search", "")):  # these characters are finder syntax and cannot be escaped
        raise ValueError(f"Oracle search term may not contain , ; or =: {src['search']!r}")
    keyword = f",keyword={src['search']}" if src.get("search") else ""
    jobs, offset, total, empty_retried = [], 0, None, False
    while total is None or offset < total:
        finder = f"findReqs;siteNumber={src['site']}{keyword},limit=200,offset={offset},sortBy=POSTING_DATES_DESC"
        r = SESSION.get(url, params={"onlyData": "true", "expand": "requisitionList.secondaryLocations",
                                      "finder": finder}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        item = r.json()["items"][0]
        total = item["TotalJobsCount"]
        page = item.get("requisitionList", [])
        if not page:
            if empty_retried:
                break
            empty_retried = True
            time.sleep(1)
            continue
        empty_retried = False
        jobs += page
        offset += 200
        time.sleep(0.1)
    return {"total": total, "requisitionList": jobs}


def normalize_oracle(src, raw):
    out, seen = [], set()
    for j in raw["requisitionList"]:
        if j["Id"] in seen:
            continue
        seen.add(j["Id"])
        out.append(_row(src, j["Id"], j.get("Title"),
                        f"https://{src['host']}/hcmUI/CandidateExperience/en/sites/{src['site']}/job/{j['Id']}",
                        j.get("PrimaryLocation", ""), j.get("JobFunction", ""), _iso_date(j.get("PostedDate"))))
    return out


def reported_total(raw):
    """The total a paged board says it has, or None for boards that return everything in one response."""
    if isinstance(raw, dict):
        return raw.get("total", raw.get("totalFound"))
    return None


FETCH = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
         "smartrecruiters": fetch_smartrecruiters, "workday": fetch_workday, "oracle": fetch_oracle}
NORMALIZE = {"greenhouse": normalize_greenhouse, "lever": normalize_lever, "ashby": normalize_ashby,
             "smartrecruiters": normalize_smartrecruiters, "workday": normalize_workday,
             "oracle": normalize_oracle}

SOURCES = [
    # Workday (banks and asset managers)
    {"name": "statestreet", "employer": "State Street", "ats": "workday", "tenant": "statestreet", "wd": "wd1", "site": "Global"},
    {"name": "invesco", "employer": "Invesco", "ats": "workday", "tenant": "invesco", "wd": "wd1", "site": "IVZ"},
    {"name": "mastercard", "employer": "Mastercard", "ats": "workday", "tenant": "mastercard", "wd": "wd1", "site": "CorporateCareers"},
    {"name": "morganstanley", "employer": "Morgan Stanley", "ats": "workday", "tenant": "ms", "wd": "wd5", "site": "External"},
    {"name": "northerntrust", "employer": "Northern Trust", "ats": "workday", "tenant": "ntrs", "wd": "wd1", "site": "northerntrust"},
    {"name": "nuveen", "employer": "Nuveen (TIAA)", "ats": "workday", "tenant": "tiaa", "wd": "wd1", "site": "Search"},
    {"name": "blueowl", "employer": "Blue Owl", "ats": "workday", "tenant": "blueowl", "wd": "wd1", "site": "BlueOwl"},
    {"name": "wellington", "employer": "Wellington Management", "ats": "workday", "tenant": "wellington", "wd": "wd5", "site": "External"},
    # Oracle Recruiting Cloud: 7,000+ postings, so requested with a search term
    {"name": "jpmorgan", "employer": "JPMorgan Chase", "ats": "oracle", "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001", "search": "sustainability"},
    # Institutional asset managers and ESG data providers (Workday)
    {"name": "russell", "employer": "Russell Investments (Seattle)", "ats": "workday", "tenant": "russell", "wd": "wd5", "site": "RussellInvestments"},
    {"name": "ameriprise", "employer": "Ameriprise (Columbia Threadneedle)", "ats": "workday", "tenant": "ameriprise", "wd": "wd5", "site": "ameriprise"},
    {"name": "blackrock", "employer": "BlackRock", "ats": "workday", "tenant": "blackrock", "wd": "wd1", "site": "BlackRock_Professional"},
    {"name": "spglobal", "employer": "S&P Global", "ats": "workday", "tenant": "spgi", "wd": "wd5", "site": "SPGI_Careers"},
    {"name": "morningstar", "employer": "Morningstar (Sustainalytics)", "ats": "workday", "tenant": "morningstar", "wd": "wd5", "site": "Morningstar"},
    {"name": "vanguard", "employer": "Vanguard", "ats": "workday", "tenant": "vanguard", "wd": "wd5", "site": "vanguard_external"},
    {"name": "fidelity", "employer": "Fidelity Investments", "ats": "workday", "tenant": "fmr", "wd": "wd1", "site": "FidelityCareers"},
    {"name": "capitalgroup", "employer": "Capital Group", "ats": "workday", "tenant": "capgroup", "wd": "wd1", "site": "capitalgroupcareers"},
    {"name": "troweprice", "employer": "T. Rowe Price", "ats": "workday", "tenant": "troweprice", "wd": "wd5", "site": "TRowePrice"},
    {"name": "abrdn", "employer": "abrdn", "ats": "workday", "tenant": "abrdn", "wd": "wd3", "site": "abrdn"},
    {"name": "blackstone", "employer": "Blackstone", "ats": "workday", "tenant": "blackstone", "wd": "wd1", "site": "Blackstone_Careers"},
    {"name": "carlyle", "employer": "Carlyle", "ats": "workday", "tenant": "carlyle", "wd": "wd1", "site": "carlyle"},
    # ESG / climate specialists
    {"name": "sweep", "employer": "Sweep", "ats": "ashby", "token": "sweep"},
    {"name": "sylvera", "employer": "Sylvera", "ats": "ashby", "token": "sylvera"},
    {"name": "patch", "employer": "Patch", "ats": "greenhouse", "token": "patch"},
    {"name": "carbondirect", "employer": "Carbon Direct", "ats": "greenhouse", "token": "carbondirect"},
    {"name": "ecovadis", "employer": "EcoVadis", "ats": "smartrecruiters", "token": "ecovadis"},
    # Greenhouse (fintech)
    {"name": "stripe", "employer": "Stripe", "ats": "greenhouse", "token": "stripe"},
    {"name": "coinbase", "employer": "Coinbase", "ats": "greenhouse", "token": "coinbase"},
    {"name": "robinhood", "employer": "Robinhood", "ats": "greenhouse", "token": "robinhood"},
    {"name": "affirm", "employer": "Affirm", "ats": "greenhouse", "token": "affirm"},
    {"name": "sofi", "employer": "SoFi", "ats": "greenhouse", "token": "sofi"},
    {"name": "carta", "employer": "Carta", "ats": "greenhouse", "token": "carta"},
    {"name": "brex", "employer": "Brex", "ats": "greenhouse", "token": "brex"},
    {"name": "betterment", "employer": "Betterment", "ats": "greenhouse", "token": "betterment"},
    {"name": "chime", "employer": "Chime", "ats": "greenhouse", "token": "chime"},
    # Ashby (climate software / fintech)
    {"name": "watershed", "employer": "Watershed", "ats": "ashby", "token": "watershed"},
    {"name": "ramp", "employer": "Ramp", "ats": "ashby", "token": "ramp"},
    # Lever
    {"name": "arcadia", "employer": "Arcadia", "ats": "lever", "token": "arcadia"},
    # SmartRecruiters
    {"name": "experian", "employer": "Experian", "ats": "smartrecruiters", "token": "Experian"},
]


# What kind of employer each source is. "asset manager" means an investment management firm; the
# am_esg flag (see titlerule.py) only applies to those. Banks that own an asset-management arm
# (State Street, Northern Trust, Morgan Stanley, JPMorgan) are classed as banks.
EMPLOYER_TYPE = {
    **dict.fromkeys(["invesco", "nuveen", "blueowl", "wellington", "russell", "ameriprise", "blackrock",
                     "vanguard", "fidelity", "capitalgroup", "troweprice", "abrdn", "blackstone", "carlyle"],
                    "asset manager"),
    **dict.fromkeys(["statestreet", "northerntrust", "morganstanley", "jpmorgan"], "bank"),
    **dict.fromkeys(["spglobal", "morningstar", "experian"], "ratings and data"),
    **dict.fromkeys(["sweep", "sylvera", "patch", "carbondirect", "ecovadis", "watershed", "arcadia"],
                    "sustainability vendor"),
    **dict.fromkeys(["mastercard", "stripe", "coinbase", "robinhood", "affirm", "sofi", "carta", "brex",
                     "betterment", "chime", "ramp"], "fintech"),
}


def employer_type(source_name):
    return EMPLOYER_TYPE.get(source_name, "other")
