// Every Market-page number, computed from the history rows alone.
// first_run postings were already open when watching began, so their start date is unknown and
// they are left out wherever a start date is needed.
function median(a) {
  if (!a.length) return null;
  const s = [...a].sort((x, y) => x - y), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function countBy(rows, key) {
  const m = new Map();
  for (const r of rows) { const k = key(r); if (k) m.set(k, (m.get(k) || 0) + 1); }
  return m;
}

function dateRange(from, to) {
  const out = [];
  for (let d = dayNum(from); d <= dayNum(to); d++) out.push(new Date(d * 86400000).toISOString().slice(0, 10));
  return out;
}

function computeMarket(rows, latest) {
  const days = rows.length ? dateRange(rows.reduce((m, r) => (r.first_seen < m ? r.first_seen : m), latest), latest) : [];
  const fresh = rows.filter(r => !r.first_run);
  const newAll = countBy(fresh, r => r.first_seen), newRole = countBy(fresh.filter(r => r.in_role), r => r.first_seen);
  const gone = countBy(rows, r => r.removed_date);
  const open = rows.filter(r => r.status === "open");
  const perEmployer = [...countBy(open, r => r.employer)].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const perLocation = [...countBy(open, r => r.location)].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const lifetimes = fresh.filter(r => r.status === "removed" && r.removed_date).map(r => daysBetween(r.first_seen, r.removed_date));
  const eligible = fresh.filter(r => daysBetween(r.first_seen, latest) >= 7);
  const quick = eligible.filter(r => r.removed_date && daysBetween(r.first_seen, r.removed_date) <= 7);
  return {
    days,
    newAll: days.map(d => newAll.get(d) || 0),
    newRole: days.map(d => newRole.get(d) || 0),
    removed: days.map(d => gone.get(d) || 0),
    perEmployer, perLocation,
    openCount: open.length,
    removedCount: lifetimes.length,
    medianDaysOpen: median(lifetimes),
    eligibleCount: eligible.length,
    quickCount: quick.length,
    shareWithin7: eligible.length ? quick.length / eligible.length : null,
  };
}

if (typeof module !== "undefined") module.exports = { computeMarket, median };
