# Job Watcher

[![tests](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml)

A tool that watches the ESG / sustainability job market. Every day GitHub Actions pulls the open postings from 18 employers' job boards, compares them with what it saw before, records what is new and what is gone, opens a GitHub Issue for the day, and publishes the result to a GitHub Pages site.

- **Role watched:** ESG / sustainability / stewardship analyst work.
- **Site:** https://slriggss.github.io/job-watcher/
- Every board is read as JSON with no login. No HTML is scraped.

## Files

| File | What it does |
|---|---|
| `jobwatcher/sources.py` | The watch list, how each applicant tracking system is called, and the conversion of each to the common columns |
| `jobwatcher/titlerule.py` | The title rule that marks a posting in role or not |
| `jobwatcher/build.py` | Builds `data/history.csv` from the raw files alone; also computes the status counts |
| `jobwatcher/pipeline.py` | The daily run: fetch every source, write raw files, build history, write status, open the day's Issue |
| `tests/test_sources.py` | Conversion of every source to the common columns |
| `tests/test_titlerule.py` | The title rule |
| `tests/test_build.py` | First-seen, last-seen, removed and reopened logic; the history is reproduced from raw files |
| `tests/test_market.py`, `tests/market_check.js` | Runs the Market page's own code in Node and checks it against an independent Python calculation |
| `.github/workflows/daily.yml` | Runs the pipeline once a day (07:23 UTC) and commits the data |
| `.github/workflows/tests.yml` | Runs pytest on every push |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day, compressed; a failed source has no file |
| `data/raw/<date>/results.json` | The result (ok, count, error) of every source that day |
| `data/history.csv` | One row per posting, built from the raw files |
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
| morganstanley | Morgan Stanley | Workday |
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
| palantir | Palantir | Lever |
| spotify | Spotify | Lever |
| experian | Experian | SmartRecruiters |

No board returns more than 5,000 postings, so no search term is used.

## Title rule

A posting is **in role** when its title (case-insensitive, whole words) contains one of: `esg`, `sustainab…`, `stewardship`, `climate`, `decarbonisation/decarbonization`, `net zero`, `carbon`, `responsible invest…`, `impact invest…`, `proxy voting|research|advis…|analyst…`, `corporate responsibility`, `corporate governance`, `environmental`, `social impact`, `ethics`, `energy transition` — **unless** it also contains `data governance`, `model governance`, `environmental health` or `EHS`. The rule is applied when the history is built, so changing it changes every day of the history.

## Rebuild the history from the raw files

```
uv run python -m jobwatcher.build
```

Run the whole pipeline locally (without opening an Issue) with `uv run python -m jobwatcher.pipeline --no-issue`. Run the tests with `uv run pytest`.

## How history is built

For each raw date in order, per source: a posting seen for the first time gets that day as `first_seen`; every posting listed gets that day as `last_seen`; an open posting is marked `removed` (with that day as `removed_date`) when the source has a raw file that day and no longer lists it; a removed posting listed again becomes `open` with `removed_date` cleared and `first_seen` unchanged. `first_run` is true for postings listed in the first raw file of their source. A day on which a source failed leaves that source's postings untouched.
