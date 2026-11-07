// Browse page: filters, the shortlist, and the posting rows. Needs app.js (loadData, esc, postingTag, shortDate).
const SHORTLIST_KEY = "jobwatcher.shortlist";
const PAGE = 100;
const FILTER_IDS = ["q", "loc", "etype", "employer", "days", "sort"];
const URL_NAMES = { q: "q", loc: "loc", etype: "type", employer: "employer", days: "days", sort: "sort" };

let shortlist = new Set();
try { shortlist = new Set(JSON.parse(localStorage.getItem(SHORTLIST_KEY) || "[]")); } catch (e) { /* no storage: the shortlist lasts until reload */ }
const saveShortlist = () => { try { localStorage.setItem(SHORTLIST_KEY, JSON.stringify([...shortlist])); } catch (e) { /* ignore */ } };

let allRows = [], openRows = [], latest = "", scope = "role", limit = PAGE, undoTimer = null;

const plural = (n, one, many) => `${n.toLocaleString()} ${n === 1 ? one : many}`;

// ---- state in the address bar, so a filtered view survives a reload and can be shared ----
function readUrl() {
  const p = new URLSearchParams(location.search);
  scope = ["role", "am", "all", "short"].includes(p.get("scope")) ? p.get("scope") : "role";
  for (const id of FILTER_IDS) if (p.has(URL_NAMES[id])) $("#" + id).value = p.get(URL_NAMES[id]);
}
function writeUrl() {
  const p = new URLSearchParams();
  if (scope !== "role") p.set("scope", scope);
  for (const id of FILTER_IDS) { const v = $("#" + id).value; if (v && !(id === "sort" && v === "desc")) p.set(URL_NAMES[id], v); }
  const qs = p.toString();
  try { history.replaceState(null, "", qs ? "?" + qs : location.pathname); } catch (e) { /* ignore */ }
}

function clearFilters() {
  for (const id of FILTER_IDS) $("#" + id).value = id === "sort" ? "desc" : "";
  fillEmployers(); limit = PAGE; view();
}
const filtersActive = () => FILTER_IDS.some(id => $("#" + id).value && !(id === "sort" && $("#" + id).value === "desc"));

// ---- the controls ----
function fillEmployers() {
  const type = $("#etype").value, sel = $("#employer"), keep = sel.value;
  const emps = [...new Set(openRows.filter(r => !type || r.employer_type === type).map(r => r.employer))].sort();
  sel.innerHTML = `<option value="">All employers</option>` + emps.map(e => `<option>${esc(e)}</option>`).join("");
  sel.value = emps.includes(keep) ? keep : "";
}

function fillDays() {
  const span = Math.max(1, ...openRows.map(r => r.daysOpen));
  const steps = [1, 3, 7, 14, 30, 90].filter(t => t <= span);  // only choices the history is long enough to tell apart
  const keep = $("#days").value;
  $("#days").innerHTML = `<option value="">Any</option>` + steps.map(t => `<option value="${t}">${t} day${t === 1 ? "" : "s"} or fewer</option>`).join("");
  $("#days").value = steps.includes(+keep) ? keep : "";
}

function updateShortlistButton() {
  $("#scope [data-v=short]").textContent = `Shortlist (${shortlist.size})`;
}

// ---- rows ----
function rowHtml(r) {
  const starred = shortlist.has(r.posting_id), removed = r.status === "removed";
  const isNew = r.first_seen === latest && !r.first_run;
  const when = removed ? `Removed ${shortDate(r.removed_date)}`
    : r.first_run ? `Open ${r.daysOpen}+ days` : `First seen ${shortDate(r.first_seen)}`;
  const name = `${r.title} at ${r.employer}`;
  return `<li class="${starred ? "starred" : ""}${removed ? " gone" : ""}${isIntl(r) ? " intl" : ""}" data-id="${esc(r.posting_id)}">
    <button type="button" class="star ${starred ? "on" : ""}" data-id="${esc(r.posting_id)}" aria-pressed="${starred}" aria-label="Shortlist: ${esc(name)}" title="${starred ? "Remove from shortlist" : "Save to shortlist"}">${starSvg(starred)}</button>
    <div class="main"><div class="t"><a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>${isNew && !removed ? '<span class="tag new">New</span>' : ""}${removed ? '<span class="tag gone">Removed</span>' : ""}${postingTag(r, scope)}</div>
      <div class="m">${esc(r.employer)}${placeHtml(r)} · ${esc(when)}</div></div>
    ${removed ? "" : `<a class="apply" href="${esc(r.url)}" target="_blank" rel="noopener" aria-label="Apply: ${esc(name)} (opens in a new tab)">Apply</a>`}</li>`;
}

function matches(r) {
  const words = $("#q").value.toLowerCase().split(/\s+/).filter(Boolean), title = r.title.toLowerCase();
  const loc = $("#loc").value.trim().toLowerCase(), maxDays = +$("#days").value;
  const etype = $("#etype").value, emp = $("#employer").value;
  return (scope === "all" || (scope === "am" ? r.am_esg : r.in_role)) && (!etype || r.employer_type === etype) &&
    (!emp || r.employer === emp) && words.every(w => title.includes(w)) &&
    (!loc || (r.location + " " + r.location_norm + " " + r.locations_all).toLowerCase().includes(loc)) &&
    (!maxDays || r.daysOpen <= maxDays);
}

function emptyMessage(scopeIsShort) {
  if (scopeIsShort) return `<li class="empty">Your shortlist is empty. Tap the star on any posting to save it here.</li>`;
  const bits = [];
  const add = (label, v) => { if (v) bits.push(`${label} “${esc(v)}”`); };
  add("search", $("#q").value.trim()); add("location", $("#loc").value.trim()); add("type", $("#etype").value);
  add("employer", $("#employer").value); if ($("#days").value) bits.push(`open ${esc($("#days").value)} days or fewer`);
  const scopeName = { role: "In my role", am: "Asset-manager ESG", all: "All postings" }[scope];
  return `<li class="empty"><p>No postings match ${bits.length ? bits.join(", ") + " in" : ""} “${scopeName}”.</p>` +
    `<p>${filtersActive() ? '<button type="button" class="linklike" data-act="clear">Clear search and filters</button> · ' : ""}` +
    `${scope !== "all" ? '<button type="button" class="linklike" data-act="all">Show all postings</button>' : ""}</p></li>`;
}

function view() {
  const isShort = scope === "short";
  $("#controls").hidden = isShort;  // the shortlist is its own view, independent of the filters
  $("#clear").hidden = isShort || !filtersActive();
  document.querySelectorAll("#scope button").forEach(b => { const on = b.dataset.v === scope; b.classList.toggle("on", on); b.setAttribute("aria-pressed", on); });
  let out;
  if (isShort) {
    out = allRows.filter(r => shortlist.has(r.posting_id));  // removed postings stay, marked as removed
  } else {
    out = openRows.filter(matches);
    const dir = $("#sort").value === "asc" ? 1 : -1;
    out.sort((a, b) => dir * a.first_seen.localeCompare(b.first_seen) || a.posting_id.localeCompare(b.posting_id));
  }
  $("#count").textContent = isShort ? `${plural(out.length, "saved posting", "saved postings")}` : plural(out.length, "posting", "postings");
  $("#list").innerHTML = out.slice(0, limit).map(rowHtml).join("") || emptyMessage(isShort);
  $("#more").hidden = out.length <= limit;
  updateShortlistButton();
  writeUrl();
}

// ---- starring updates only that row, so keyboard focus stays on the star ----
function toast(html) {
  const t = $("#toast");
  t.innerHTML = html; t.hidden = false;
  clearTimeout(undoTimer);
  undoTimer = setTimeout(() => { t.hidden = true; }, 8000);
}

function setStar(id, on, { announce = true } = {}) {
  on ? shortlist.add(id) : shortlist.delete(id);
  saveShortlist();
  const li = $(`#list li[data-id="${CSS.escape(id)}"]`);
  if (li) {
    const b = li.querySelector(".star");
    li.classList.toggle("starred", on); b.classList.toggle("on", on);
    b.setAttribute("aria-pressed", on); b.innerHTML = starSvg(on);
    b.title = on ? "Remove from shortlist" : "Save to shortlist";
    if (on) { b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop"); }
  }
  updateShortlistButton();
  if (announce && !on) toast(`Removed from shortlist. <button type="button" class="linklike" data-undo="${esc(id)}">Undo</button>`);
  else if (announce) $("#toast").hidden = true;
}

function init(data) {
  allRows = data.rows.map(r => ({ ...r, daysOpen: daysBetween(r.first_seen, data.latest) }));
  latest = data.latest;
  openRows = allRows.filter(r => r.status === "open");
  const types = [...new Set(openRows.map(r => r.employer_type).filter(Boolean))].sort();
  $("#etype").insertAdjacentHTML("beforeend", types.map(t => `<option value="${esc(t)}">${esc(typeLabel(t))}</option>`).join(""));
  readUrl();
  fillEmployers(); fillDays();
  const p = new URLSearchParams(location.search);  // a value from the address bar that depends on the lists above
  if (p.has("employer")) $("#employer").value = p.get("employer");
  if (p.has("days")) $("#days").value = p.get("days");
  view();
}

function wire() {
  for (const id of FILTER_IDS) $("#" + id).addEventListener("input", () => { if (id === "etype") fillEmployers(); limit = PAGE; view(); });
  $("#scope").addEventListener("click", e => {
    const b = e.target.closest("button"); if (!b) return;
    scope = b.dataset.v; limit = PAGE; view();
  });
  $("#clear").addEventListener("click", clearFilters);
  $("#more").addEventListener("click", () => { limit += 200; view(); });
  $("#list").addEventListener("click", e => {
    const star = e.target.closest(".star");
    if (star) { setStar(star.dataset.id, !shortlist.has(star.dataset.id)); return; }
    const act = e.target.closest("[data-act]");
    if (act && act.dataset.act === "clear") clearFilters();
    if (act && act.dataset.act === "all") { scope = "all"; limit = PAGE; view(); }
  });
  $("#toast").addEventListener("click", e => {
    const u = e.target.closest("[data-undo]");
    if (u) { setStar(u.dataset.undo, true, { announce: false }); $("#toast").hidden = true; }
  });
  // "/" jumps to the search box
  addEventListener("keydown", e => {
    if (e.key === "/" && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); $("#q").focus(); }
  });
}

renderNav("browse.html");
wire();
loadData().then(init).catch(showError);
