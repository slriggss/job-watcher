// Draws each chart into a stub card of a given width and prints the SVG, for tests/test_charts.py.
// Usage: node tests/charts_check.js <card width in px>
const fs = require("fs"), vm = require("vm"), path = require("path");
const root = path.join(__dirname, "..");
const width = +process.argv[2];
const stubEl = { addEventListener() {}, setAttribute() {}, classList: { add() {}, remove() {}, toggle() {} } };
const fakeSvg = { querySelector: () => stubEl, querySelectorAll: () => [], getBoundingClientRect: () => ({ left: 0, width }) };
const makeCard = () => ({ clientWidth: width, html: "", classList: { add() {}, contains: () => false },
  set innerHTML(v) { this.html = v; }, get innerHTML() { return this.html; }, querySelector: () => fakeSvg });
const ctx = { console, navigator: {}, document: {}, window: {}, innerWidth: width, addEventListener() {}, setTimeout, clearTimeout };
vm.createContext(ctx);
for (const f of ["app.js", "charts.js"]) vm.runInContext(fs.readFileSync(path.join(root, f), "utf8"), ctx, { filename: f });
const employers = ["Morgan Stanley", "Fidelity Investments", "State Street", "Ameriprise (Columbia Threadneedle)", "S&P Global"];
const days = ["2026-10-29", "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"];
const out = {};
for (const [name, call] of Object.entries({
  hbar: "hBarChart(card, employers, [1217, 900, 700, 650, 300], 'open', 10268)",
  bar: "barChart(card, days, [0, 5, 9, 12, 3, 4, 8, 20, 7], 'removed')",
  line: "lineChart(card, days, [{ name: 'All postings', values: [0, 200, 300, 250, 210, 220, 230, 240, 230] }, { name: 'In my role', values: [0, 1, 2, 0, 3, 1, 0, 2, 0] }])",
})) {
  const card = makeCard();
  ctx.card = card; ctx.employers = employers; ctx.days = days;
  vm.runInContext(call, ctx);
  out[name] = card.html;
}
console.log(JSON.stringify(out));
