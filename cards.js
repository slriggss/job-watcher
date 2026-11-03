// The four cards at the top of the Today page.
//  1. A flip calendar: the number of days with a successful run flips from 1 up to today's value when the page
//     loads, then stays there. The row of seven dots lights up as it passes the 7 days the assignment needs.
//  2-4. Open / new / removed: the number counts up, with the change since yesterday and a small trend line.
// Needs app.js (dayNum, esc) and market.js (computeMarket) to be loaded first.
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

function flipCalendar(el, target, monthLabel) {
  const width = String(target).length, pad = v => String(v).padStart(width, "0");
  const dots = Array.from({ length: MIN_DAYS }, () => `<i class="dot-d"></i>`).join("");
  el.innerHTML = `<div class="cal-head"><span class="rings"></span><span>Days run</span><span>${esc(monthLabel)}</span></div>` +
    `<div class="cal-body"><div class="flip"></div><div class="dots">${dots}</div>` +
    `<div class="l" id="cal-note">days with a successful run</div></div>`;
  const flip = el.querySelector(".flip"), dotEls = [...el.querySelectorAll(".dot-d")], note = el.querySelector("#cal-note");
  const tiles = pad(1).split("").map(makeTile);
  tiles.forEach(t => flip.appendChild(t));
  const show = v => {
    pad(v).split("").forEach((d, i) => flipTile(tiles[i], d, stepMs * 0.9));
    dotEls.forEach((d, i) => d.classList.toggle("on", i < v));
  };
  const finish = () => {
    note.innerHTML = target >= MIN_DAYS
      ? `<b class="met">✓ ${MIN_DAYS}-day minimum met</b> · days with a successful run`
      : `${target} of ${MIN_DAYS} needed · days with a successful run`;
  };
  const stepMs = Math.max(70, Math.min(230, 1700 / Math.max(1, target)));
  if (reducedMotion() || target <= 1) {
    pad(target).split("").forEach((d, i) => { tiles[i].querySelectorAll(".half span").forEach(s => { s.textContent = d; }); });
    dotEls.forEach((d, i) => d.classList.toggle("on", i < target));
    finish(); return;
  }
  let v = 1; show(1);
  const timer = setInterval(() => {
    v += 1; show(v);
    if (v >= target) { clearInterval(timer); setTimeout(finish, stepMs); }
  }, stepMs);
}

function countUp(el, to, ms = 1100) {
  if (reducedMotion() || to === 0) { el.textContent = to.toLocaleString(); return; }
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
  const W = 120, H = 30, P = 3, lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
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
  return d === 0 ? "no change since yesterday" : `${d > 0 ? "▲" : "▼"} ${Math.abs(d).toLocaleString()} since yesterday`;
}

function renderCards(el, status, rows, latest) {
  const m = computeMarket(rows, latest);
  const openSeries = m.days.map(d => rows.filter(r => r.first_seen <= d && (!r.removed_date || r.removed_date > d)).length);
  const month = new Date(latest + "T00:00:00Z").toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" }).toUpperCase();
  const stats = [
    ["open", "Open postings", openSeries, "open"], ["new_today", "New today", m.newAll, "new"],
    ["removed_today", "Removed today", m.removed, "gone"],
  ];
  // Each card gets its own hover: a magnifying lens (open), a rising sun (new), slash marks (removed).
  const extras = {
    open: "",
    new: `<span class="dawn" aria-hidden="true"><i class="sky"></i><i class="sun"></i></span>`,
    gone: `<svg class="slashes" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">` +
          `<line pathLength="1" x1="-4" y1="14" x2="104" y2="52"/><line pathLength="1" x1="-4" y1="50" x2="104" y2="96"/>` +
          `<line pathLength="1" x1="22" y1="-4" x2="86" y2="104"/></svg>`,
  };
  el.innerHTML = `<div class="card cal" id="cal"></div>` + stats.map(([k, label, series, kind]) =>
    `<div class="card stat ${kind}">${extras[kind]}<div class="l">${label}</div><div class="n" data-to="${status[k]}">0</div>` +
    `<div class="delta">${deltaLine(series)}</div>${sparkline(series, label)}</div>`).join("");
  flipCalendar($("#cal"), status.days_with_success, month);
  el.querySelectorAll(".n[data-to]").forEach(n => countUp(n, +n.dataset.to));
  attachLens(el.querySelector(".stat.open"));
}

// A magnifying glass that follows the pointer over the Open postings card and shows the number enlarged.
function attachLens(card, zoom = 2, radius = 46) {
  if (!card || typeof PointerEvent === "undefined") return;
  const num = card.querySelector(".n");
  const lens = document.createElement("div");
  lens.className = "lens"; lens.setAttribute("aria-hidden", "true");
  lens.innerHTML = `<div class="lens-glass"><span class="lens-num"></span></div><i class="lens-handle"></i>`;
  card.appendChild(lens);
  const big = lens.querySelector(".lens-num");
  const move = e => {
    if (e.pointerType === "touch") return;
    const c = card.getBoundingClientRect(), r = num.getBoundingClientRect();
    const mx = e.clientX - c.left, my = e.clientY - c.top;
    lens.style.transform = `translate(${mx - radius}px, ${my - radius}px)`;
    big.textContent = num.textContent;   // follows the count-up
    // a point P of the card lands at radius + zoom * (P - pointer) inside the glass
    big.style.left = `${radius + zoom * (r.left - c.left - mx)}px`;
    big.style.top = `${radius + zoom * (r.top - c.top - my)}px`;
    big.style.transform = `scale(${zoom})`;
    lens.classList.add("on");
  };
  card.addEventListener("pointermove", move);
  card.addEventListener("pointerenter", move);
  card.addEventListener("pointerleave", () => lens.classList.remove("on"));
}
