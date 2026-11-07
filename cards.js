// The four cards at the top of the Today page.
//  1. A flip calendar of the days the tool has been running. It rests on the current number and rolls up from 1
//     to it on the first hover of each visit (it does not replay until the page is opened again). The other numbers
//     count up, but only the first time a visitor sees a new run: on later visits (or a return from Browse)
//     the final numbers are shown at once.
//  2-4. Open / new / removed: each is a link (to Browse, and to the lists below), with the change since
//     yesterday and a small trend line.
// Hovering the four cards plays their effects: the calendar rolls up to today's number, a magnifying glass
// enlarges everything on the Open card, a sun rises behind New, and Removed is crossed out.
// Needs app.js (dayNum, esc, shortDate) and market.js (computeMarket) to be loaded first.
const MIN_DAYS = 7;
const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

function makeTile(d) {
  const t = document.createElement("div");
  t.className = "tile";
  t.innerHTML = `<div class="half top"><span>${d}</span></div><div class="half bot"><span>${d}</span></div>` +
    `<div class="half top flap-t"><span>${d}</span></div><div class="half bot flap-b"><span>${d}</span></div>`;
  return t;
}

function flipTile(t, to, ms) {
  const [top, bot, flapTop, flapBot] = t.querySelectorAll(".half");
  const set = (h, v) => { h.firstChild.textContent = v; };
  if (bot.firstChild.textContent === to) return;
  const old = bot.firstChild.textContent;
  set(top, to); set(flapTop, old); set(flapBot, to);   // the top half shows the new digit behind the falling flap
  t.classList.remove("go"); void t.offsetWidth;        // restart the animation
  t.style.setProperty("--ms", ms + "ms"); t.classList.add("go");
  setTimeout(() => { set(bot, to); t.classList.remove("go"); }, ms);
}

function flipCalendar(el, target, monthLabel, since) {
  const width = String(target).length, pad = v => String(v).padStart(width, "0");
  const dots = Array.from({ length: MIN_DAYS }, () => `<span class="dot-d"></span>`).join("");
  el.innerHTML = `<div class="cal-head"><span class="rings"></span><span>Days</span><span>${esc(monthLabel)}</span></div>` +
    `<div class="cal-body"><div class="flip"></div><div class="dots">${dots}</div>` +
    `<div class="l" id="cal-note">${esc(noteText(target, since))}</div></div>`;
  const flip = el.querySelector(".flip"), dotEls = [...el.querySelectorAll(".dot-d")];
  const tiles = pad(1).split("").map(makeTile);
  tiles.forEach(t => flip.appendChild(t));
  const stepMs = Math.max(70, Math.min(230, 1700 / Math.max(1, target)));
  const setNow = v => {  // no animation: put the digits and dots straight at v
    pad(v).split("").forEach((d, i) => tiles[i].querySelectorAll(".half span").forEach(sp => { sp.textContent = d; }));
    dotEls.forEach((d, i) => d.classList.toggle("on", i < v));
  };
  const flipTo = v => {
    pad(v).split("").forEach((d, i) => flipTile(tiles[i], d, stepMs * 0.9));
    dotEls.forEach((d, i) => d.classList.toggle("on", i < v));
  };
  setNow(target);  // at rest it shows today's number
  let timer = null, played = false;
  const rollUp = () => {  // the first hover on each visit: start at 1 and flip up to the current number of days
    if (played || timer || reducedMotion() || target <= 1) return;
    played = true;
    let v = 1; setNow(1);
    timer = setInterval(() => {
      v += 1; flipTo(v);
      if (v >= target) { clearInterval(timer); setTimeout(() => { timer = null; }, stepMs); }
    }, stepMs);
  };
  el.addEventListener("pointerenter", rollUp);
}

// "Watching since Oct 29": the visitor's reason to care, not the course requirement
const noteText = (days, since) => `days of data${since ? ", watching since " + shortDate(since) : ""}`;

function countUp(el, to, ms = 1100, animate = true) {
  if (!animate || reducedMotion() || to === 0) { el.textContent = to.toLocaleString(); return; }
  const t0 = performance.now();
  const tick = now => {
    const p = Math.min(1, (now - t0) / ms), eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(to * eased).toLocaleString();
    if (p < 1) requestAnimationFrame(tick); else el.textContent = to.toLocaleString();
  };
  requestAnimationFrame(tick);
}

function sparkline(values, label) {
  if (values.length < 2) return "";
  const W = 120, H = 30, P = 3, lo = Math.min(0, ...values), hi = Math.max(...values), span = hi - lo || 1;
  const x = i => P + (i * (W - 2 * P)) / (values.length - 1), y = v => H - P - ((v - lo) / span) * (H - 2 * P);
  const pts = values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`);
  const last = values.length - 1;
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(label)} by day">` +
    `<path class="spark-area" d="M${x(0)},${H} L${pts.join(" L")} L${x(last)},${H} Z"/>` +
    `<path class="spark-ln" pathLength="1" d="M${pts.join(" L")}"/>` +
    `<circle class="spark-dot" cx="${x(last).toFixed(1)}" cy="${y(values[last]).toFixed(1)}" r="3"/></svg>`;
}

function deltaLine(series) {
  if (series.length < 2) return "";
  const d = series[series.length - 1] - series[series.length - 2];
  return d === 0 ? "no change since yesterday" : `${d > 0 ? "↑" : "↓"} ${Math.abs(d).toLocaleString()} since yesterday`;
}

const LAST_RUN_KEY = "jobwatcher.lastRunShown";

function renderCards(el, status, rows, latest) {
  const m = computeMarket(rows, latest);
  const openSeries = m.days.map(d => rows.filter(r => r.first_seen <= d && (!r.removed_date || r.removed_date > d)).length);
  const month = new Date(latest + "T00:00:00Z").toLocaleString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase();
  // The first day cannot have new postings by definition, so the "new" trend starts on the second day.
  const stats = [
    ["open", "Open postings", openSeries, "open", "browse.html?scope=all"],
    ["new_today", "New today", m.newAll.slice(1), "new", "#new-h"],
    ["removed_today", "Removed today", m.removed, "gone", "#gone-h"],
  ];
  // Each card has its own hover: a lens (open), a rising sun (new), an X through the card (removed).
  const extras = {
    open: "",
    new: `<span class="dawn" aria-hidden="true"><i class="sky"></i><i class="sun"></i></span>`,
    gone: `<svg class="slashes" aria-hidden="true"></svg>`,  // filled in by attachSlashes, in real pixels
  };
  let seen = null;
  try { seen = localStorage.getItem(LAST_RUN_KEY); localStorage.setItem(LAST_RUN_KEY, status.run_time); } catch (e) { /* no storage: animate */ }
  const animate = seen !== status.run_time;  // animate once per new run
  el.classList.toggle("still", !animate);
  el.innerHTML = `<div class="card cal" id="cal"></div>` + stats.map(([k, label, series, kind, href]) =>
    `<a class="card stat ${kind}" href="${href}">${extras[kind]}<div class="l">${label}</div><div class="n" data-to="${status[k]}">${animate ? 0 : (+status[k]).toLocaleString()}</div>` +
    `<div class="delta">${deltaLine(series)}</div>${sparkline(series, label)}</a>`).join("");
  flipCalendar($("#cal"), status.days_with_success, month, status.first_run_date);
  attachLens(el.querySelector(".stat.open"));
  attachSlashes(el.querySelector(".stat.gone"));
  if (animate) el.querySelectorAll(".n[data-to]").forEach(n => countUp(n, +n.dataset.to));
}

// A magnifying glass that follows the pointer over the Open postings card and enlarges everything under it:
// the label, the number, the change line and the trend line, not just the number.
function attachLens(card, zoom = 1.5, radius = 58) {
  if (!card || typeof PointerEvent === "undefined") return;
  const lens = document.createElement("div");
  lens.className = "lens"; lens.setAttribute("aria-hidden", "true");
  lens.innerHTML = `<div class="lens-glass"><div class="lens-copy card stat open"></div></div><i class="lens-handle"></i>`;
  card.appendChild(lens);
  const copy = lens.querySelector(".lens-copy");
  const sync = () => {  // a fresh copy of the card's content each time, so it follows the count-up
    const keep = [...card.children].filter(c => c !== lens && !c.classList.contains("dawn") && !c.classList.contains("slashes"));
    copy.innerHTML = keep.map(c => c.outerHTML).join("");
    copy.style.width = card.clientWidth + "px";
    copy.style.height = card.clientHeight + "px";
  };
  const move = e => {
    if (e.pointerType === "touch") return;
    const c = card.getBoundingClientRect(), mx = e.clientX - c.left, my = e.clientY - c.top;
    lens.style.transform = `translate(${mx - radius}px, ${my - radius}px)`;
    sync();
    // the card point under the pointer lands at the centre of the glass, enlarged by `zoom`
    copy.style.transform = `translate(${radius - zoom * mx}px, ${radius - zoom * my}px) scale(${zoom})`;
    lens.classList.add("on");
  };
  card.addEventListener("pointermove", move);
  card.addEventListener("pointerenter", move);
  card.addEventListener("pointerleave", () => lens.classList.remove("on"));
}

// The X over the Removed card. Drawn in the card's real pixel size (and redrawn if the card is resized) so each
// stroke's dash length is exact: it is invisible until hovered and gone again as soon as the pointer leaves.
function attachSlashes(card) {
  const svg = card && card.querySelector(".slashes");
  if (!svg) return;
  const draw = () => {
    const w = card.clientWidth, h = card.clientHeight, m = 10, len = Math.hypot(w - 2 * m, h - 2 * m).toFixed(1);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.innerHTML = `<line x1="${m}" y1="${m}" x2="${w - m}" y2="${h - m}" style="--len:${len}"/>` +
                    `<line x1="${w - m}" y1="${m}" x2="${m}" y2="${h - m}" style="--len:${len}"/>`;
  };
  draw();
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(draw).observe(card);
}
