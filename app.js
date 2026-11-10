// Shared by all three pages: navigation bar, data loading, small helpers.
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// The brand mark: a cream diamond with a W, matching the app icon.
const MARK = `<svg class="mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 1L23 12L12 23L1 12Z"/><text x="12" y="16.5" text-anchor="middle">W</text></svg>`;
const THEME_ICON = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 0 18V3Z"/><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/></svg>`;

function renderNav(active) {
  const links = [["index.html", "Today"], ["browse.html", "Browse"], ["market.html", "Market"]];
  document.body.insertAdjacentHTML("afterbegin",
    `<a class="skip" href="#main">Skip to content</a>` +
    `<nav aria-label="Main"><a class="brand" href="index.html">${MARK}Watch Jobber</a><span class="tabs">` +
    links.map(([h, t]) => `<a href="${h}" class="${h === active ? "on" : ""}"${h === active ? ' aria-current="page"' : ""}>${t}</a>`).join("") +
    `</span><button type="button" class="theme" aria-label="Switch between light and dark" title="Light / dark">${THEME_ICON}</button></nav>`);
  const main = $("main"); if (main && !main.id) main.id = "main";
  $("nav .theme").addEventListener("click", () => setTheme(effectiveTheme() === "dark" ? "light" : "dark"));
}

// Light or dark: always starts dark, whatever the system setting, and remembers the visitor's own choice.
const THEME_KEY = "jobwatcher.theme", THEME_COLORS = { light: "#7a2f3a", dark: "#5e1f2b" };
const effectiveTheme = () => document.documentElement.dataset.theme ||
  "dark";
function setTheme(t, remember = true) {
  document.documentElement.dataset.theme = t;
  const metas = document.querySelectorAll('meta[name="theme-color"]');  // one colour now, whatever the system says
  metas.forEach((m, i) => { if (i) m.remove(); else { m.removeAttribute("media"); m.content = THEME_COLORS[t]; } });
  if (remember) { try { localStorage.setItem(THEME_KEY, t); } catch (e) { /* ignore */ } }
}
try { const saved = localStorage.getItem(THEME_KEY); if (saved === "light" || saved === "dark") setTheme(saved, false); } catch (e) { /* no storage */ }

// Star icons (drawn, not text glyphs, so they look the same everywhere)
const starSvg = on => `<svg class="star-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2.6l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.5l-5.9 3.1 1.2-6.5L2.5 9.5l6.6-.9Z" fill="${on ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>`;
// A posting outside the United States gets a country chip ("London · UK") only (the row itself is not tinted).
// Postings whose country is unknown (no single place yet, or just "Remote") are left plain.
const isIntl = r => !!r.country && r.country !== "US";
function placeHtml(r) {
  const place = r.location_norm || r.location;
  if (!place) return "";
  if (!isIntl(r)) return " · " + esc(place);
  const i = place.lastIndexOf(", ");
  const label = i > 0 ? place.slice(0, i) + " · " + place.slice(i + 2) : place;
  return ` · <span class="chip intl" title="Outside the United States: ${esc(place)}">${esc(label)}</span>`;
}
// "bank" -> "Bank", "ratings and data" -> "Ratings and data"
const typeLabel = t => (t ? t[0].toUpperCase() + t.slice(1) : "");

const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
// "2026-11-05" -> "Nov 5"; anything else is returned as it is
const shortDate = s => (/^\d{4}-\d\d-\d\d$/.test(s || "") ? `${MONTH_NAMES[+s.slice(5, 7) - 1]} ${+s.slice(8)}` : s || "");

// The small tag after a posting's title. "In my role" is left off when the page already shows only role postings.
function postingTag(r, scope = "all") {
  if (r.in_role) return scope === "role" ? "" : '<span class="tag">in role</span>';
  if (!r.am_esg) return "";
  const why = "Asset-manager ESG, matched on " + r.esg_via + (r.esg_terms ? ": " + r.esg_terms.replace(/;/g, ", ") : "");
  return `<span class="tag" title="${esc(why)}">ESG</span>`;
}

function parseCSV(text) {
  const rows = []; let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(cell); cell = ""; rows.push(row); row = [];
    } else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const head = rows.shift();
  return rows.filter(r => r.length === head.length).map(r => {
    const o = Object.fromEntries(head.map((h, i) => [h, r[i]]));
    o.in_role = o.in_role === "true"; o.am_esg = o.am_esg === "true"; o.first_run = o.first_run === "true";
    return o;
  });
}

// The service worker answers from its cache when the network is down, so this still works offline.
async function loadData() {
  const [csv, status] = await Promise.all([
    fetch("data/history.csv").then(r => { if (!r.ok) throw new Error("history.csv " + r.status); return r.text(); }),
    fetch("data/status.json").then(r => { if (!r.ok) throw new Error("status.json " + r.status); return r.json(); }),
  ]);
  const rows = parseCSV(csv);
  if (typeof navigator !== "undefined" && navigator.onLine === false) offlineNotice(status);
  return { rows, status, latest: latestDate(rows) };
}

// The date of the last run as the history sees it: the newest date in any date column.
function latestDate(rows) {
  let d = "";
  for (const r of rows) for (const k of ["first_seen", "last_seen", "removed_date"]) if (r[k] > d) d = r[k];
  return d;
}

const dayNum = s => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) / 86400000;
const daysBetween = (a, b) => dayNum(b) - dayNum(a);

// Just the time, in Central time ("9:12 AM CST", or CDT in summer); the heading above already has the date
const fmtTime = iso => new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/Chicago", timeZoneName: "short" });
const fmtRun = iso => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });

// Shown above the page content when the visitor is offline and the page is drawn from the cached run.
function offlineNotice(status) {
  const main = $("main");
  if (main && !$(".notice")) main.insertAdjacentHTML("afterbegin",
    `<p class="notice" role="status">Offline, showing the run of ${esc(fmtRun(status.run_time))}.</p>`);
}

// One error panel for every page: what failed, what to do, and a way to try again.
function showError(e) {
  const offline = typeof navigator !== "undefined" && navigator.onLine === false;
  $("main").innerHTML = `<div class="error-panel" role="alert"><h2>Could not load the latest data</h2>` +
    `<p>${offline ? "You appear to be offline and this page has no saved copy of the data yet. Open it once while online." :
      "The data did not load (" + esc(e.message) + "). The site may be updating; this usually clears in a minute."}</p>` +
    `<button type="button" onclick="location.reload()">Try again</button></div>`;
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
