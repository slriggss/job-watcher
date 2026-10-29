// Loads the site's own app.js + market.js, runs computeMarket on a history.csv, prints JSON.
// Usage: node tests/market_check.js <history.csv> <latest-date>
const fs = require("fs"), vm = require("vm"), path = require("path");
const root = path.join(__dirname, "..");
const ctx = { navigator: {}, document: {}, console };
vm.createContext(ctx);
for (const f of ["app.js", "market.js"]) vm.runInContext(fs.readFileSync(path.join(root, f), "utf8"), ctx, { filename: f });
const rows = vm.runInContext("parseCSV", ctx)(fs.readFileSync(process.argv[2], "utf8"));
const m = vm.runInContext("computeMarket", ctx)(rows, process.argv[3] || vm.runInContext("latestDate", ctx)(rows));
console.log(JSON.stringify({ ...m, perEmployer: m.perEmployer, perLocation: m.perLocation }));
