// Runs app.js's pure helpers in Node and prints the results as JSON, for tests/test_app.py.
const fs = require("fs"), vm = require("vm"), path = require("path");
const ctx = { console, navigator: {}, document: {}, addEventListener() {}, matchMedia: () => ({ matches: true }) };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "app.js"), "utf8"), ctx, { filename: "app.js" });
const run = code => vm.runInContext(code, ctx);
const role = { in_role: true, am_esg: false }, esg = { in_role: false, am_esg: true, esg_via: "text", esg_terms: "esg:3;stewardship:1" };
ctx.csvText = ["a,b", "1,2", "3", "4,5"].join("\n"); ctx.role = role; ctx.esg = esg; ctx.plain = { in_role: false, am_esg: false };
console.log(JSON.stringify({
  shortDate: [run("shortDate('2026-11-05')"), run("shortDate('2026-10-29')"), run("shortDate('')"), run("shortDate('abc')")],
  roleOnRolePage: run("postingTag(role, 'role')"), roleElsewhere: run("postingTag(role, 'all')"),
  esg: run("postingTag(esg, 'am')"), plain: run("postingTag(plain)"),
  csv: run("parseCSV(csvText)").length,
}));
