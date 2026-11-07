# Watch Jobber

[![tests](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/tests.yml)
[![daily](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/slriggss/job-watcher/actions/workflows/daily.yml)

Watch Jobber (repository name: `job-watcher`) is a tool that watches the ESG / sustainability job market. Every day GitHub Actions pulls the open postings from 39 employers' job boards, compares them with what it saw before, records what is new and what is gone, opens a GitHub Issue for the day, and publishes the result to a GitHub Pages site.

- **Role watched:** ESG / sustainability / stewardship analyst work.
- **Site:** https://slriggss.github.io/job-watcher/
- Every board is read as JSON with no login. No HTML is scraped.

## Files

| File | What it does |
|---|---|
| `jobwatcher/sources.py` | The watch list, how each applicant tracking system is called, and the conversion of each to the common columns |
| `jobwatcher/titlerule.py` | The title rule that marks a posting in role or not |
| `jobwatcher/enrich.py` | Fetches and saves the detail response of Workday postings that need it (asset-manager text, full location lists) |
| `jobwatcher/terms.py` | The ESG term list and the scan that counts it in saved text |
| `jobwatcher/locations.py` | Turns the many spellings of a location into one place (`location_norm`) and a remote flag |
| `jobwatcher/build.py` | Builds `data/history.csv` from the raw files (including the saved detail files); also computes the status counts |
| `jobwatcher/pipeline.py` | The daily run: fetch every source (retries, completeness check), write raw files safely, build history, write status |
| `jobwatcher/issue.py` | Opens or updates the day's GitHub Issue from the files the pipeline wrote (its own workflow step, the only one with a token) |
| `tests/test_sources.py` | Conversion of every source to the common columns |
| `tests/test_titlerule.py` | The title rule |
| `tests/test_enrich.py` | The term scan, saved detail files, back-off when a site refuses, rebuilding from saved files, and the text routes into the asset-manager flag |
| `tests/test_locations.py` | Location spellings collapse to one place; remote flag; "N Locations" is not a place |
| `tests/test_site_files.py` | The service worker's file list, the `?v=` on every script, the manifest and the theme colors agree with the files that exist |
| `tests/test_facts.py`, `tests/facts_check.js` | A dated fact shows on its date, the nearest one fills the gaps, every day from Nov 7 through Jan 31 has a dated fact within a week, and the list is well formed |
| `tests/test_app.py`, `tests/app_check.js` | The shared page helpers (dates, posting tags, CSV parser) run in Node |
| `tests/test_charts.py`, `tests/charts_check.js` | Draws the Market charts in Node at phone and desktop widths and checks size, names and axes |
| `tests/test_build.py` | First-seen, last-seen, removed and reopened logic; the history is reproduced from raw files |
| `tests/test_pipeline.py` | Same-day reruns, short pulls, source health, the issue text and which issues get closed |
| `tests/test_market.py`, `tests/market_check.js` | Runs the Market page's own code in Node and checks it against an independent Python calculation |
| `.github/workflows/daily.yml` | Main run at 01:07 UTC and a backup at 10:41 UTC that does nothing if the day is already stored; commits the data, then updates the issue |
| `.github/workflows/tests.yml` | Runs pytest (with Node) on every push |
| `data/raw/<date>/<source>.json.gz` | What each source returned that day, compressed; a failed source has no file |
| `data/raw/<date>/results.json` | The result (ok, count, error) of every source that day |
| `data/raw/details/<source>/<id>.json.gz` | The detail response of each posting that needed it, saved once; the build computes term counts, the location list and the start date from these |
| `data/raw/<date>/details.json` | Which detail files that run fetched, and which sources refused |
| `data/history.csv` | One row per posting, built from the raw files |
| `data/enrich.csv` | Legacy: term counts of postings read before descriptions were saved. A fallback only; it is no longer written and is ignored for a posting once that posting's detail file exists |
| `data/status.json` | Describes the latest run |
| `index.html` | Today page: last run time, source status, the four counts, new and removed postings |
| `browse.html`, `browse.js` | Browse page: scope switch (role, asset-manager ESG, all, shortlist), filters kept in the address bar, word-by-word title search, rows with title links and an Apply button, a shortlist that is its own view and keeps removed postings |
| `market.html`, `market.js`, `charts.js` | Market page: six findings computed in the browser from `history.csv`, with inline-SVG charts |
| `cards.js` | The four stat cards on the Today page |
| `facts.js` | The hand-written list of women-in-business facts and the picker for the Today page: a fact on its own date, else the nearest dated fact within a week (labelled with its real date), else an undated fact. Dated entries cover November through January so far |
| `app.js`, `style.css` | Shared navigation bar, data loading, CSV parser, fonts and colors |
| `fonts/` | EB Garamond (titles, headings, large numbers) and Inter (interface text), self-hosted, each with its SIL Open Font License |
| `pyproject.toml`, `uv.lock`, `.python-version` | Dependencies and the Python version (3.12) |
| `.gitattributes`, `.gitignore` | Git line-ending rules and ignored files |
| `manifest.webmanifest`, `sw.js`, `icon.svg`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` | Make the site installable and usable offline (network first with a 4-second limit on data requests; the data files are cached at install; only page navigations fall back to `index.html`) |

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

A posting is **in role** when its title (case-insensitive, whole words) contains one of: `esg`, `sustainab…`, `stewardship`, `climate`, `decarbonisation/decarbonization`, `net zero`, `carbon`, `responsible invest…`, `impact invest…`, `proxy voting|research|advis…|analyst…`, `corporate responsibility`, `corporate governance`, `environmental`, `social impact`, `ethics`, `energy transition` — or when it contains both `compliance` or `risk` and `analyst` (so "Senior Compliance Analyst" and "Risk Analyst II" are in role, "Compliance Manager" is not), or when it contains `policy` (except accounting, credit, cyber, security and insurance policy, and legal roles) or an engagement phrase with a stewardship word (`issuer`, `shareholder`, `investor`, `company`, `corporate`, `ESG`, `stakeholder`, `stewardship`, `climate`, `sustainability`, `proxy` or `active` engagement; a bare "engagement" is mostly client or consulting work and is not matched) — **unless** it also contains `data governance`, `model governance`, `environmental health` or `EHS`. The rule is applied when the history is built, so changing it changes every day of the history.

## Asset-manager ESG

A second flag, **`am_esg`**, applies only to the 14 employers classed as **asset managers** (Invesco, Nuveen, Blue Owl, Wellington Management, Russell Investments, Ameriprise/Columbia Threadneedle, BlackRock, Vanguard, Fidelity, Capital Group, T. Rowe Price, abrdn, Blackstone, Carlyle). Banks with an asset-management arm (State Street, Northern Trust, Morgan Stanley, JPMorgan) are classed as banks. The `esg_via` column says why a posting qualifies:

- **title**: it is in role, or the title has `proxy`, `issuer/shareholder/investor/company/corporate/ESG engagement`, `engagement analyst|specialist|associate` or `responsible` (not a web proxy, not client or employee engagement). A bare "governance" is deliberately excluded: at asset managers it nearly always means IT, data, operations or fund-board governance.
- **text**: the posting text mentions ESG terms at least 3 times. An identical pattern of terms in 3 or more postings of one employer is treated as that employer's company paragraph and ignored.
- **risk/compliance text**: the title has risk, compliance, regulatory, legal, counsel, audit, controls, oversight, conduct, policy or ethics, and the text mentions ESG terms at least twice.

ESG terms in text: `ESG`, `environmental, social`, `stewardship`, `proxy voting`, `responsible/sustainable/impact invest…`, `climate risk|change|transition`, `net zero`, `TCFD`, `SFDR`, `ISSB`, `CSRD`, `greenwash…`, `corporate governance`, `sustainable finance`, `sustainability-linked`. `esg_terms` lists which were found and how often.

**How the text is read.** For each open asset-manager posting on Workday, and for any Workday posting whose list location is only "N Locations", `enrich.py` asks the same public job-board service the daily run uses for that posting's detail (2 requests at a time, a pause of about a second between them) and saves the response compressed under `data/raw/details/`. Each posting is fetched once; the backlog and new postings are fetched a little each run (at most 100 a run, postings read before descriptions were saved first, then risk and compliance titles), so no employer sees a burst. A first attempt at 600 requests in a few minutes made nine employers answer 403 to everything, which is why the pace is slow. If a site answers 403 or 429, or a source keeps failing, that source is left alone for 7 days (recorded in `details/_blocked.json`) and does not use up the run's slots. Carlyle's board has been seen refusing detail requests (403), although 13 Carlyle postings are in `data/enrich.csv`; Carlyle postings not yet read can only qualify by title. Reading text never blocks the daily run: a failure there is logged as a warning and the day's data is still written. Backfill by hand with `uv run python -m jobwatcher.enrich`.

The build scans the saved files on every rebuild, so changing the term list in `terms.py` or the thresholds in `titlerule.py` reaches every posting already read. The history is reproducible from the raw folder; the one exception is the postings still carried by the legacy `data/enrich.csv`, which shrink as those postings are fetched again (the `text_read` column is `true` for any posting with a saved or legacy reading, so an unread posting can be told from one read with no ESG terms). The boilerplate rule (an identical term pattern in 3 or more postings of one employer is ignored) is computed over whatever has been read at build time, so a few early flags can change as the backlog is read.

## Locations

`location` keeps the board's original text. `location_norm` is one place per posting (`New York, NY`, `Pune, India`, `Remote, US`), built by `locations.py`: about 20 spellings of New York become one, US states become two-letter codes, and a list of places (separated by `;`) uses its first. `locations_all` lists every place when the full list is known, and `remote` is true if any location says remote. For a posting listing "N Locations", the full list comes from the saved detail file, so those postings are placed as their detail files are fetched. Until then `location_norm` is empty and the Market page says how many open postings are unplaced. Known limits: a two-letter country code that is also a US state (Colombia, "CO") is read as the state, and a bare city name is placed only for a short list of unambiguous cities.

## Rebuild the history from the raw files

```
uv run python -m jobwatcher.build
```

Run the tests with `uv run pytest` (Python 3.12 and Node are needed; the Market and chart tests run the pages' code in Node).

Running `uv run python -m jobwatcher.pipeline --no-issue` does a real pull: it writes today's raw folder, `data/history.csv` and `data/status.json` in your working copy, so do not commit its output by hand (the daily run would then conflict on rebase).

## How history is built

For each raw date in order, per source: a posting seen for the first time gets that day as `first_seen`; every posting listed gets that day as `last_seen`; an open posting is marked `removed` (with that day as `removed_date`) when the source has a raw file that day and no longer lists it; a removed posting listed again becomes `open` with `removed_date` cleared and `first_seen` unchanged. `first_run` is true for postings listed in the first raw file of their source. A day on which a source failed leaves that source's postings untouched. A listing with a blank field (no title, no location) does not overwrite the earlier value.

**Safeguards on a pull.** A board that returns fewer than 95% of the total it reports is treated as failed, so a short pull cannot mark real postings removed. A same-day rerun writes to a scratch folder and swaps it in only if at least one source succeeded; a source that fails in the rerun keeps its earlier file from that day, and `results.json` is never deleted. `status.json` lists, per source, the last date it succeeded and a `suspect` flag when its count fell below half of its last good day.

## Seattle focus

Seattle institutional asset managers are covered through Russell Investments (headquartered in Seattle) and through large boards that post Seattle roles (Morgan Stanley, which includes Parametric, and Fidelity). Use the Location filter on the Browse page (type `Seattle`) to see them.

## Design notes

- **Type:** EB Garamond for page titles, headings and large numbers; Inter for everything read or operated (labels, fields, rows, chart text). Sizes: 13, 15, 18, 24, 32 and 44 px.
- **Colors, one job each:** burgundy is the brand and anything interactive; ochre is the shortlist only; green is new postings and "in role"; muted rose is removed postings; red is failures, always with a word.
- **Today:** the three counts are links (Open goes to Browse, New and Removed jump to their lists), with a quiet hover. The flip calendar is the one signature piece. The counts animate once per new run, not on every visit.
- **Header:** fixed at the top with the brand mark; on a phone the three pages are a bottom tab bar. A light/dark toggle starts from the system setting and remembers the choice.
- **Loading:** placeholder blocks the size of the content, with a slow faint shimmer, instead of empty headings.
- **Market:** each section opens with its key number, then the chart, then the explanation. The first day is the baseline: it cannot have new or removed postings, so those charts and averages start on the second day.
- **Printing:** charts are drawn complete when printed.
