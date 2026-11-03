# Job Watcher

[![tests](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml)

A tool that watches the ESG / sustainability job market. Every day GitHub Actions pulls the open postings from 39 employers' job boards, compares them with what it saw before, records what is new and what is gone, opens a GitHub Issue for the day, and publishes the result to a GitHub Pages site.

- **Role watched:** ESG / sustainability / stewardship analyst work.
- **Site:** https://slriggss.github.io/job-watcher/
- Every board is read as JSON with no login. No HTML is scraped.

## Files

| File | What it does |
|---|---|
| `jobwatcher/sources.py` | The watch list, how each applicant tracking system is called, and the conversion of each to the common columns |
| `jobwatcher/titlerule.py` | The title rule that marks a posting in role or not |
| `jobwatcher/enrich.py` | Reads the text of asset-manager postings once and counts ESG terms in it (see Asset-manager ESG) |
| `jobwatcher/build.py` | Builds `data/history.csv` from the raw files (plus `data/enrich.csv`); also computes the status counts |
| `jobwatcher/pipeline.py` | The daily run: fetch every source, write raw files, build history, write status, open the day's Issue |
| `tests/test_sources.py` | Conversion of every source to the common columns |
| `tests/test_titlerule.py` | The title rule |
| `tests/test_enrich.py` | The term scan, caching, back-off when a site refuses, and the text routes into the asset-manager flag |
| `tests/test_build.py` | First-seen, last-seen, removed and reopened logic; the history is reproduced from raw files |
| `tests/test_market.py`, `tests/market_check.js` | Runs the Market page's own code in Node and checks it against an independent Python calculation |
| `.github/workflows/daily.yml` | Runs the pipeline once a day (07:23 UTC) and commits the data |
| `.github/workflows/tests.yml` | Runs pytest on every push |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day, compressed; a failed source has no file |
| `data/raw/<date>/results.json` | The result (ok, count, error) of every source that day |
| `data/history.csv` | One row per posting, built from the raw files and `data/enrich.csv` |
| `data/enrich.csv` | One row per asset-manager posting whose text has been read: ESG-term count and the terms found (the text itself is not stored) |
| `data/status.json` | Describes the latest run |
| `index.html` | Today page: last run time, source status, the four counts, new and removed postings |
| `browse.html` | Browse page: open postings with in-role switch, filters, title search, first-seen sort, apply links, starred shortlist |
| `market.html`, `market.js`, `charts.js` | Market page: six findings computed in the browser from `history.csv`, with inline-SVG charts |
| `app.js`, `style.css` | Shared navigation bar, data loading, CSV parser, fonts and colors |
| `manifest.webmanifest`, `sw.js`, `icon.svg`, `icon-192.png`, `icon-512.png` | Make the site installable and usable offline (network first, cache as fallback) |

## Sources

| Source | Employer | Applicant tracking system |
|---|---|---|
| statestreet | State Street | Workday |
| invesco | Invesco | Workday |
| mastercard | Mastercard | Workday |
| morganstanley | Morgan Stanley (includes Calvert Research and Management postings) | Workday |
| northerntrust | Northern Trust | Workday |
| nuveen | Nuveen (hosted on TIAA's board) | Workday |
| blueowl | Blue Owl | Workday |
| wellington | Wellington Management | Workday |
| jpmorgan | JPMorgan Chase | Oracle Recruiting Cloud |
| russell | Russell Investments (Seattle headquarters) | Workday |
| ameriprise | Ameriprise (parent of Columbia Threadneedle) | Workday |
| blackrock | BlackRock | Workday |
| spglobal | S&P Global | Workday |
| morningstar | Morningstar (parent of Sustainalytics) | Workday |
| vanguard | Vanguard | Workday |
| fidelity | Fidelity Investments | Workday |
| capitalgroup | Capital Group | Workday |
| troweprice | T. Rowe Price | Workday |
| abrdn | abrdn | Workday |
| blackstone | Blackstone | Workday |
| carlyle | Carlyle | Workday |
| sweep | Sweep | Ashby |
| sylvera | Sylvera | Ashby |
| patch | Patch | Greenhouse |
| carbondirect | Carbon Direct | Greenhouse |
| ecovadis | EcoVadis | SmartRecruiters |
| stripe | Stripe | Greenhouse |
| coinbase | Coinbase | Greenhouse |
| robinhood | Robinhood | Greenhouse |
| affirm | Affirm | Greenhouse |
| sofi | SoFi | Greenhouse |
| carta | Carta | Greenhouse |
| brex | Brex | Greenhouse |
| betterment | Betterment | Greenhouse |
| chime | Chime | Greenhouse |
| watershed | Watershed | Ashby |
| ramp | Ramp | Ashby |
| arcadia | Arcadia (clean-energy data) | Lever |
| experian | Experian | SmartRecruiters |

JPMorgan Chase's board returns more than 5,000 postings (7,307 when checked), so it is requested with the search term **`sustainability`**; the other 38 boards are read in full. Workday sometimes lists a stub with only a requisition id (no title, no link); those are skipped.

## Title rule

A posting is **in role** when its title (case-insensitive, whole words) contains one of: `esg`, `sustainab…`, `stewardship`, `climate`, `decarbonisation/decarbonization`, `net zero`, `carbon`, `responsible invest…`, `impact invest…`, `proxy voting|research|advis…|analyst…`, `corporate responsibility`, `corporate governance`, `environmental`, `social impact`, `ethics`, `energy transition` — **unless** it also contains `data governance`, `model governance`, `environmental health` or `EHS`. The rule is applied when the history is built, so changing it changes every day of the history.

## Asset-manager ESG

A second flag, **`am_esg`**, applies only to the 14 employers classed as **asset managers** (Invesco, Nuveen, Blue Owl, Wellington Management, Russell Investments, Ameriprise/Columbia Threadneedle, BlackRock, Vanguard, Fidelity, Capital Group, T. Rowe Price, abrdn, Blackstone, Carlyle). Banks with an asset-management arm (State Street, Northern Trust, Morgan Stanley, JPMorgan) are classed as banks. The `esg_via` column says why a posting qualifies:

- **title**: it is in role, or the title has `proxy`, `issuer/shareholder/investor/company/corporate/ESG engagement`, `engagement analyst|specialist|associate` or `responsible` (not a web proxy, not client or employee engagement). A bare "governance" is deliberately excluded: at asset managers it nearly always means IT, data, operations or fund-board governance.
- **text**: the posting text mentions ESG terms at least 3 times. An identical pattern of terms in 3 or more postings of one employer is treated as that employer's company paragraph and ignored.
- **risk/compliance text**: the title has risk, compliance, regulatory, legal, counsel, audit, controls, oversight, conduct, policy or ethics, and the text mentions ESG terms at least twice.

ESG terms in text: `ESG`, `environmental, social`, `stewardship`, `proxy voting`, `responsible/sustainable/impact invest…`, `climate risk|change|transition`, `net zero`, `TCFD`, `SFDR`, `ISSB`, `CSRD`, `greenwash…`, `corporate governance`, `sustainable finance`, `sustainability-linked`. `esg_terms` lists which were found and how often.

**How the text is read.** For each open asset-manager posting on Workday, `enrich.py` asks the same public job-board service the daily run uses for that posting's detail (2 requests at a time, a pause of about a second between them), counts the terms, and appends a row to `data/enrich.csv`. Each posting is read once; the backlog and new postings are read a little each run (at most 100 a run, risk and compliance titles first), so no employer sees a burst. A first attempt at 600 requests in a few minutes made nine employers answer 403 to everything, which is why the pace is slow. If a site answers 403 or 429, or a source keeps failing, that source is left alone for the rest of the run, and any failure is retried on a later day. Carlyle's board refuses detail requests (403), so Carlyle postings can only qualify by title. Reading text never blocks the daily run: a failure there is logged as a warning and the day's data is still written. Backfill by hand with `uv run python -m jobwatcher.enrich`.

The history is reproducible from the raw files together with `data/enrich.csv`.

## Rebuild the history from the raw files

```
uv run python -m jobwatcher.build
```

Run the whole pipeline locally (without opening an Issue) with `uv run python -m jobwatcher.pipeline --no-issue`. Run the tests with `uv run pytest`.

## How history is built

For each raw date in order, per source: a posting seen for the first time gets that day as `first_seen`; every posting listed gets that day as `last_seen`; an open posting is marked `removed` (with that day as `removed_date`) when the source has a raw file that day and no longer lists it; a removed posting listed again becomes `open` with `removed_date` cleared and `first_seen` unchanged. `first_run` is true for postings listed in the first raw file of their source. A day on which a source failed leaves that source's postings untouched.

## Seattle focus

Seattle institutional asset managers are covered through Russell Investments (headquartered in Seattle) and through large boards that post Seattle roles (Morgan Stanley, which includes Parametric, and Fidelity). Use the Location filter on the Browse page (type `Seattle`) to see them.
