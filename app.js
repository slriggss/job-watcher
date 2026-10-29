// Shared by all three pages: navigation bar, data loading, small helpers.
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function renderNav(active) {
  const links = [["index.html", "Today"], ["browse.html", "Browse"], ["market.html", "Market"]];
  document.body.insertAdjacentHTML("afterbegin",
    `<nav><span class="brand">Job Watcher</span>` +
    links.map(([h, t]) => `<a href="${h}" class="${h === active ? "on" : ""}">${t}</a>`).join("") + `</nav>`);
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
    o.in_role = o.in_role === "true"; o.first_run = o.first_run === "true";
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

function showError(e) {
  $("main").innerHTML = `<p class="empty">Could not load the data (${esc(e.message)}). Try again when online.</p>`;
}

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
