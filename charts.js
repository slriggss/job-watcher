// Inline-SVG charts (no external library, so they also work offline).
// Every chart is drawn at the width of its card, in real pixels, so the text is the same size on a phone as on a
// desktop; a chart is redrawn when its card changes width. Charts reveal themselves as they scroll into view
// (see the chart-anim rules in style.css) and respond to hover, touch and keyboard focus with a tooltip.
const CHART_H = 280, PAD = { l: 44, r: 12, t: 24, b: 44 };
const COLORS = ["color-mix(in srgb, var(--good) 55%, var(--card))", "var(--good)"];
const CHAR_PX = 7;  // average width of one label character at the chart's 13px text size
let chartUid = 0;

const dayLabel = shortDate;  // "2026-11-05" -> "Nov 5" (from app.js)
const clip = (l, max) => (l.length > max ? l.slice(0, Math.max(1, max - 1)) + "…" : l);

// The axis maximum and tick step: round numbers (1, 2, 2.5, 5 times a power of ten), just above the data.
function niceScale(v, ticks = 4) {
  if (v <= 4) return { max: 4, step: 1 };
  const raw = v / ticks, p = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(m => m * p).find(s => s >= raw);
  return { max: Math.ceil(v / step) * step, step };
}

function frame(w, scale, padR = PAD.r) {
  let s = "";
  for (let v = 0; v <= scale.max + 1e-9; v += scale.step) {
    const y = PAD.t + (CHART_H - PAD.t - PAD.b) * (1 - v / scale.max);
    s += `<line x1="${PAD.l}" x2="${w - padR}" y1="${y}" y2="${y}" stroke="var(--line)"/>` +
         `<text x="${PAD.l - 6}" y="${y + 4}" text-anchor="end">${Math.round(v).toLocaleString()}</text>`;
  }
  return `<g class="grid">${s}</g>`;
}

// ---- tooltip: one floating element shared by every chart ----
let tipEl = null;
function showTip(html, x, y) {
  if (!tipEl) {
    tipEl = document.createElement("div");
    tipEl.className = "tip"; tipEl.setAttribute("aria-hidden", "true");
    document.body.appendChild(tipEl);
  }
  tipEl.innerHTML = html; tipEl.classList.add("on");
  const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
  let l = x + 16, t = y - h - 12;
  if (l + w > innerWidth - 8) l = x - w - 16;
  if (l < 8) l = 8;
  if (t < 8) t = y + 18;
  tipEl.style.transform = `translate(${l}px, ${t}px)`;
}
function hideTip() { if (tipEl) tipEl.classList.remove("on"); }

// ---- reveal on scroll: hold the chart in its "before" state until it is mostly on screen ----
function reveal(el) {
  const reduced = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || !("IntersectionObserver" in window)) return;
  el.classList.add("chart-anim");
  const io = new IntersectionObserver(entries => {
    if (entries.some(e => e.isIntersecting)) { el.classList.add("in"); io.disconnect(); }
  }, { threshold: 0.35 });
  io.observe(el);
}

const pointOf = (e, node) => {
  if (e && e.clientX != null && (e.clientX || e.clientY)) return [e.clientX, e.clientY];
  const r = node.getBoundingClientRect();
  return [r.left + r.width / 2, r.top];
};

// Draw a chart now, and again whenever its card changes width. draw(width) fills the card.
const charts = new Set();
function mount(el, draw) {
  const width = () => Math.max(280, Math.floor(el.clientWidth - 24) || 640);  // 24 = the card's padding
  let drawn = 0;
  const paint = () => {
    const w = width();
    if (w === drawn) return;
    if (drawn) el.classList.add("redrawn");  // a redraw must not replay the entry animation
    drawn = w; draw(w);
  };
  paint(); reveal(el);
  charts.add(paint);
}
let resizeTimer = null;
if (typeof addEventListener === "function") {
  addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => charts.forEach(p => p()), 150); });
}

// series: [{name, values}] sharing one list of labels
function lineChart(el, labels, series) {
  mount(el, SVG_W => {
    const id = ++chartUid, n = labels.length, { max, step: tickStep } = niceScale(Math.max(1, ...series.flatMap(s => s.values)));
    const R = SVG_W >= 520 ? 104 : PAD.r, direct = SVG_W >= 520;  // room to label each line at its right end
    const colour = k => series[k].color || COLORS[k % 2];
    const iw = SVG_W - PAD.l - R, base = CHART_H - PAD.b;
    const x = i => PAD.l + (n === 1 ? iw / 2 : (i * iw) / (n - 1));
    const y = v => PAD.t + (CHART_H - PAD.t - PAD.b) * (1 - v / max);
    let s = `<defs>` + series.map((_, k) =>
      `<linearGradient id="area${id}-${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${colour(k)};stop-opacity:.32"/>` +
      `<stop offset="1" style="stop-color:${colour(k)};stop-opacity:0"/></linearGradient>`).join("") + `</defs>` + frame(SVG_W, { max, step: tickStep }, R);
    const step = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(iw / 56))));  // about 56px for each date label
    labels.forEach((l, i) => { if (i % step === 0) s += `<text x="${x(i)}" y="${CHART_H - PAD.b + 18}" text-anchor="middle">${dayLabel(l)}</text>`; });
    series.forEach((se, k) => {
      const pts = se.values.map((v, i) => `${x(i)},${y(v)}`);
      s += `<path class="area" d="M${x(0)},${base} L${pts.join(" L")} L${x(n - 1)},${base} Z" fill="url(#area${id}-${k})"/>` +
           `<path class="ln" pathLength="1" d="M${pts.join(" L")}" fill="none" stroke="${colour(k)}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    });
    s += `<line class="guide" x1="0" x2="0" y1="${PAD.t}" y2="${base}"/>`;
    series.forEach((se, k) => {
      s += se.values.map((v, i) => `<circle class="dot" data-k="${k}" data-i="${i}" style="--i:${i}" cx="${x(i)}" cy="${y(v)}" r="3.8" fill="${colour(k)}"/>`).join("");
    });
    if (direct) {  // name each line where it ends, nudged apart if the ends are close
      const ends = series.map((se, k) => ({ k, y: y(se.values[n - 1]) })).sort((a, b) => a.y - b.y);
      for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 15) ends[i].y = ends[i - 1].y + 15;
      ends.forEach(e => { s += `<text x="${x(n - 1) + 10}" y="${e.y + 4}" fill="${colour(e.k)}" style="font-weight:600;fill:${colour(e.k)}">${esc(series[e.k].name)}</text>`; });
    } else {
      let lx = PAD.l;
      series.forEach((se, k) => { s += `<circle cx="${lx + 5}" cy="${CHART_H - 10}" r="5" fill="${colour(k)}"/><text x="${lx + 14}" y="${CHART_H - 6}">${esc(se.name)}</text>`; lx += 24 + se.name.length * CHAR_PX; });
    }
    s += `<rect class="over" x="${PAD.l}" y="${PAD.t}" width="${iw}" height="${CHART_H - PAD.t - PAD.b}"/>`;
    const summary = series.map(se => `${se.name}: ${se.values.join(", ")}`).join("; ");
    el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${CHART_H}" role="img" aria-label="Line chart by day, ${esc(labels[0])} to ${esc(labels[n - 1])}. ${esc(summary)}" width="${SVG_W}" height="${CHART_H}">${s}</svg>`;

    const svg = el.querySelector("svg"), guide = svg.querySelector(".guide"), over = svg.querySelector(".over");
    const dots = [...svg.querySelectorAll(".dot")];
    let cur = -1;
    const clear = () => { cur = -1; guide.classList.remove("on"); dots.forEach(d => d.classList.remove("hot")); hideTip(); };
    over.addEventListener("pointermove", e => {
      const r = svg.getBoundingClientRect(), sx = ((e.clientX - r.left) * SVG_W) / r.width;
      const i = n === 1 ? 0 : Math.max(0, Math.min(n - 1, Math.round(((sx - PAD.l) / iw) * (n - 1))));
      if (i !== cur) {
        cur = i;
        guide.setAttribute("x1", x(i)); guide.setAttribute("x2", x(i)); guide.classList.add("on");
        dots.forEach(d => d.classList.toggle("hot", +d.dataset.i === i));
      }
      showTip(`<b>${esc(dayLabel(labels[i]))}</b>` + series.map((se, k) =>
        `<div><span class="sw" style="background:${colour(k)}"></span>${esc(se.name)}: <b>${se.values[i].toLocaleString()}</b></div>`).join(""), e.clientX, e.clientY);
    });
    over.addEventListener("pointerleave", clear);
  });
  tableToggle(el, ["Day", ...series.map(se => se.name)], labels.map((l, i) => [dayLabel(l), ...series.map(se => se.values[i].toLocaleString())]));
}

// A screen-reader and keyboard route to the numbers: "Show as table" under each chart.
function tableToggle(el, head, rows) {
  if (typeof document.createElement !== "function" || el.dataset.tabled) return;
  el.dataset.tabled = "1";
  const btn = document.createElement("button"), box = document.createElement("div");
  btn.type = "button"; btn.className = "table-toggle"; btn.textContent = "Show as table"; btn.setAttribute("aria-expanded", "false");
  box.hidden = true;
  box.innerHTML = `<table class="chart-table"><thead><tr>${head.map(h => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>` +
    `<tbody>${rows.map(r => `<tr>${r.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  btn.addEventListener("click", () => {
    box.hidden = !box.hidden; btn.textContent = box.hidden ? "Show as table" : "Hide table"; btn.setAttribute("aria-expanded", String(!box.hidden));
  });
  el.after(btn, box);
}

function wireBars(svg, labels, values, name, grand) {
  // One Tab stop for the whole chart; arrow keys move between bars. Each bar is named with its value.
  const cols = [...svg.querySelectorAll(".col")];
  cols.forEach((c, i) => {
    c.setAttribute("tabindex", i === 0 ? "0" : "-1"); c.setAttribute("role", "img");
    c.setAttribute("aria-label", `${dayLabel(labels[i])}: ${values[i].toLocaleString()} ${name}`);
    c.addEventListener("keydown", e => {
      const d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1, Home: -1e9, End: 1e9 }[e.key];
      if (d === undefined) return;
      e.preventDefault();
      const j = Math.max(0, Math.min(cols.length - 1, i + d));
      cols.forEach((x, k) => x.setAttribute("tabindex", k === j ? "0" : "-1"));
      cols[j].focus();
    });
  });
  cols.forEach(c => {
    const i = +c.dataset.i;
    const on = e => {
      c.classList.add("hot"); svg.classList.add("has-hot");
      const [px, py] = pointOf(e, c);
      const share = grand ? ` · ${((values[i] / grand) * 100).toFixed(1)}% of all ${grand.toLocaleString()}` : "";
      showTip(`<b>${esc(dayLabel(labels[i]))}</b><div><b>${values[i].toLocaleString()}</b> ${esc(name)}${share}</div>`, px, py);
    };
    const off = () => { c.classList.remove("hot"); svg.classList.remove("has-hot"); hideTip(); };
    c.addEventListener("pointerenter", on); c.addEventListener("pointermove", on); c.addEventListener("pointerleave", off);
    c.addEventListener("focus", on); c.addEventListener("blur", off);
  });
}

const barSummary = (labels, values, name) =>
  `${labels.length} bars of ${name}. Largest: ` + labels.slice(0, 3).map((l, i) => `${dayLabel(l)} ${values[i].toLocaleString()}`).join(", ");

// Vertical bars, for series in time or in order (days, days open, a two-bar split).
// grand: the total the tooltip's percentage is taken over, when the bars shown are not all of it.
// opts.mark = { at, label }: a dashed vertical line at position `at` (in bar units, 0 = first bar's centre).
function barChart(el, labels, values, name, grand = values.reduce((a, b) => a + b, 0), opts = {}) {
  mount(el, SVG_W => {
    const id = ++chartUid, n = labels.length, { max, step: tickStep } = niceScale(Math.max(1, ...values));
    const w = (SVG_W - PAD.l - PAD.r) / n, y = v => PAD.t + (CHART_H - PAD.t - PAD.b) * (1 - v / max);
    const ph = CHART_H - PAD.t - PAD.b;
    const shown = labels.map(dayLabel);
    const flat = Math.max(...shown.map(l => l.length)) * CHAR_PX < w * 0.95;  // rotate only when labels would collide
    const step = flat ? 1 : Math.max(1, Math.ceil(n / Math.max(2, Math.floor(iwLabels(SVG_W) / 22))));
    let s = frame(SVG_W, { max, step: tickStep });
    labels.forEach((l, i) => {
      const bx = PAD.l + i * w + w * 0.15, bw = w * 0.7, by = y(values[i]);
      s += `<g class="col" data-i="${i}" tabindex="0" style="--i:${i}">` +
           `<rect class="hit" x="${PAD.l + i * w}" y="${PAD.t}" width="${w}" height="${ph}"/>` +
           `<rect class="bar" x="${bx}" y="${by}" width="${bw}" height="${CHART_H - PAD.b - by}" rx="2"/>` +
           `<text class="val${n <= 12 ? " shown" : ""}" x="${bx + bw / 2}" y="${by - 6}" text-anchor="middle">${values[i].toLocaleString()}</text></g>`;
      if (i % step === 0) {
        const cx = PAD.l + i * w + w / 2, ly = CHART_H - PAD.b + 16, t = clip(shown[i], flat ? 40 : 16);
        s += flat ? `<text x="${cx}" y="${ly}" text-anchor="middle">${esc(t)}</text>`
                  : `<text x="${cx}" y="${ly}" text-anchor="end" transform="rotate(-35 ${cx} ${ly})">${esc(t)}</text>`;
      }
    });
    if (opts.mark) {
      const mx = PAD.l + (opts.mark.at + 0.5) * w;
      s += `<line class="mark-line" x1="${mx}" x2="${mx}" y1="${PAD.t - 4}" y2="${CHART_H - PAD.b}"/>` +
           `<text class="mark-label" x="${mx + 6}" y="${PAD.t + 6}">${esc(opts.mark.label)}</text>`;
    }
    el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${CHART_H}" role="img" aria-label="${esc(barSummary(labels, values, name))}${opts.mark ? ". " + esc(opts.mark.label) : ""}" width="${SVG_W}" height="${CHART_H}">${s}</svg>`;
    wireBars(el.querySelector("svg"), labels, values, name, grand);
  });
  tableToggle(el, ["Label", name], labels.map((l, i) => [dayLabel(l), values[i].toLocaleString()]));
}
const iwLabels = w => w - PAD.l - PAD.r;

// Horizontal bars, for ranked categories (employers, places): full names, sorted, value at the end of each bar.
// On a narrow card the name sits above its bar so it never has to be cut short.
function hBarChart(el, labels, values, name, grand = values.reduce((a, b) => a + b, 0)) {
  mount(el, W => {
    const n = labels.length, max = Math.max(1, ...values), narrow = W < 520;
    const longest = Math.max(...labels.map(l => l.length)) * CHAR_PX + 12;
    const nameW = narrow ? 0 : Math.min(longest, W * 0.42), valW = 56;
    const rowH = narrow ? 46 : 30, barX = nameW, barMax = W - nameW - valW, H = n * rowH + 8;
    let s = "";
    labels.forEach((l, i) => {
      const top = 4 + i * rowH, bw = Math.max(2, (values[i] / max) * barMax);
      const by = narrow ? top + 20 : top + 5, bh = narrow ? 16 : rowH - 10;
      s += `<g class="col h" data-i="${i}" tabindex="0" style="--i:${i}">` +
           `<rect class="hit" x="0" y="${top}" width="${W}" height="${rowH}"/>` +
           (narrow ? `<text x="0" y="${top + 14}">${esc(clip(l, Math.floor(W / CHAR_PX)))}</text>`
                   : `<text x="${nameW - 8}" y="${top + rowH / 2 + 4}" text-anchor="end">${esc(clip(l, Math.floor((nameW - 8) / CHAR_PX)))}</text>`) +
           `<rect class="bar" x="${barX}" y="${by}" width="${bw}" height="${bh}" rx="2"/>` +
           `<text class="val shown" x="${barX + bw + 6}" y="${by + bh / 2 + 4}">${values[i].toLocaleString()}</text></g>`;
    });
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(barSummary(labels, values, name))}" width="${W}" height="${H}">${s}</svg>`;
    wireBars(el.querySelector("svg"), labels, values, name, grand);
  });
  tableToggle(el, ["Label", name], labels.map((l, i) => [l, values[i].toLocaleString()]));
}

// A share as one split bar: parts = [{label, value}, {label, value}]
function splitBar(el, parts) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1;
  const pct = p => (100 * p.value / total).toFixed(1);
  el.innerHTML = `<div class="split-bar" role="img" aria-label="${esc(parts.map(p => `${p.label}: ${p.value.toLocaleString()} (${pct(p)}%)`).join("; "))}">` +
    parts.map((p, i) => `<div class="${i ? "b" : "a"}" style="width:${pct(p)}%">${p.value / total > 0.12 ? pct(p) + "%" : ""}</div>`).join("") + `</div>` +
    `<div class="split-legend">${parts.map(p => `<span>${esc(p.label)}: <b>${p.value.toLocaleString()}</b></span>`).join("")}</div>`;
}
