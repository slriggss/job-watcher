// Prints the fact picked for a list of dates, plus a check of the fact list itself. For tests/test_facts.py.
const { FACTS, pickFact } = require("../facts.js");
const dates = process.argv.slice(2);
console.log(JSON.stringify({
  count: FACTS.length,
  picks: dates.map(d => { const [y, m, day] = d.split("-").map(Number); return pickFact(new Date(y, m - 1, day)); }),
  facts: FACTS,
}));
