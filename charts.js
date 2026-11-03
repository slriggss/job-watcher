// Inline-SVG charts (no external library, so they also work offline).
// Charts reveal themselves as they scroll into view (see the chart-anim rules in style.css) and respond to hover,
// touch and keyboard focus with a highlight and a floating tooltip.
const SVG_W = 720, SVG_H = 280, PAD = { l: 44, r: 12, t: 24, b: 44 };
const COLORS = ["var(--accent)", "var(--accent2)"];
let chartUid = 0;

function niceMax(v) {
  if (v <= 5) return 5;
  const p = 10 ** Math.floor(Math.log10(v));
  return Math.ceil(v / p) * p;
}

function frame(max, ticks = 4) {
  let s = "";
  for (let i = 0; i <= ticks; i++) {
    const v = (max * i) / ticks, y = PAD.t + (SVG_H - PAD.t - PAD.b) * (1 - i / ticks);
    s += `<line x1="${PAD.l}" x2="${SVG_W - PAD.r}" y1="${y}" y2="${y}" stroke="var(--line)"/>` +
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

// series: [{name, values}] sharing one list of labels
function lineChart(el, labels, series) {
  const id = ++chartUid, n = labels.length, max = niceMax(Math.max(1, ...series.flatMap(s => s.values)));
  const iw = SVG_W - PAD.l - PAD.r, base = SVG_H - PAD.b;
  const x = i => PAD.l + (n === 1 ? iw / 2 : (i * iw) / (n - 1));
  const y = v => PAD.t + (SVG_H - PAD.t - PAD.b) * (1 - v / max);
  let s = `<defs>` + series.map((_, k) =>
    `<linearGradient id="area${id}-${k}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${COLORS[k % 2]};stop-opacity:.32"/>` +
    `<stop offset="1" style="stop-color:${COLORS[k % 2]};stop-opacity:0"/></linearGradient>`).join("") + `</defs>` + frame(max);
  const step = Math.max(1, Math.ceil(n / 8));
  labels.forEach((l, i) => { if (i % step === 0 || i === n - 1) s += `<text x="${x(i)}" y="${SVG_H - PAD.b + 16}" text-anchor="middle">${l.slice(5)}</text>`; });
  series.forEach((se, k) => {
    const pts = se.values.map((v, i) => `${x(i)},${y(v)}`);
    s += `<path class="area" d="M${x(0)},${base} L${pts.join(" L")} L${x(n - 1)},${base} Z" fill="url(#area${id}-${k})"/>` +
         `<path class="ln" pathLength="1" d="M${pts.join(" L")}" fill="none" stroke="${COLORS[k % 2]}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
  });
  s += `<line class="guide" x1="0" x2="0" y1="${PAD.t}" y2="${base}"/>`;
  series.forEach((se, k) => {
    s += se.values.map((v, i) => `<circle class="dot" data-k="${k}" data-i="${i}" style="--i:${i}" cx="${x(i)}" cy="${y(v)}" r="3.8" fill="${COLORS[k % 2]}"/>`).join("");
  });
  s += `<text x="${PAD.l}" y="${SVG_H - 6}">${series.map((se, k) => `<tspan fill="${COLORS[k % 2]}">● </tspan>${esc(se.name)}   `).join("")}</text>`;
  s += `<rect class="over" x="${PAD.l}" y="${PAD.t}" width="${iw}" height="${SVG_H - PAD.t - PAD.b}"/>`;
  el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" aria-label="Line chart: ${esc(series.map(se => se.name).join(" and "))} by day" width="100%">${s}</svg>`;

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
    showTip(`<b>${esc(labels[i])}</b>` + series.map((se, k) =>
      `<div><span class="sw" style="background:${COLORS[k % 2]}"></span>${esc(se.name)}: <b>${se.values[i].toLocaleString()}</b></div>`).join(""), e.clientX, e.clientY);
  });
  over.addEventListener("pointerleave", clear);
  reveal(el);
}

function barChart(el, labels, values, name) {
  const id = ++chartUid, n = labels.length, max = niceMax(Math.max(1, ...values)), total = values.reduce((a, b) => a + b, 0);
  const w = (SVG_W - PAD.l - PAD.r) / n, y = v => PAD.t + (SVG_H - PAD.t - PAD.b) * (1 - v / max);
  const ph = SVG_H - PAD.t - PAD.b;
  let s = `<defs><linearGradient id="bar${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--accent)"/><stop offset="1" style="stop-color:var(--rose)"/></linearGradient>` +
          `<linearGradient id="hot${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--accent2)"/><stop offset="1" style="stop-color:var(--accent)"/></linearGradient></defs>` + frame(max);
  const step = Math.max(1, Math.ceil(n / 24));
  labels.forEach((l, i) => {
    const bx = PAD.l + i * w + w * 0.15, bw = w * 0.7, by = y(values[i]);
    s += `<g class="col" data-i="${i}" tabindex="0" style="--i:${i}">` +
         `<rect class="hit" x="${PAD.l + i * w}" y="${PAD.t}" width="${w}" height="${ph}"/>` +
         `<rect class="bar" x="${bx}" y="${by}" width="${bw}" height="${SVG_H - PAD.b - by}" rx="2"/>` +
         `<text class="val" x="${bx + bw / 2}" y="${by - 6}" text-anchor="middle">${values[i].toLocaleString()}</text></g>`;
    if (i % step === 0) {
      const short = l.length > 14 ? l.slice(0, 13) + "…" : (/^\d{4}-/.test(l) ? l.slice(5) : l);
      s += `<text x="${bx + w * 0.35}" y="${SVG_H - PAD.b + 14}" text-anchor="end" transform="rotate(-35 ${bx + w * 0.35} ${SVG_H - PAD.b + 14})">${esc(short)}</text>`;
    }
  });
  el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" aria-label="Bar chart of ${esc(name)}, ${n} bars" width="100%" style="--g1:url(#bar${id});--g2:url(#hot${id})">${s}</svg>`;

  const svg = el.querySelector("svg");
  svg.querySelectorAll(".col").forEach(c => {
    const i = +c.dataset.i;
    const on = e => {
      c.classList.add("hot"); svg.classList.add("has-hot");
      const [px, py] = pointOf(e, c);
      const share = total ? ` · ${((values[i] / total) * 100).toFixed(1)}% of total` : "";
      showTip(`<b>${esc(labels[i])}</b><div><b>${values[i].toLocaleString()}</b> ${esc(name)}${share}</div>`, px, py);
    };
    const off = () => { c.classList.remove("hot"); svg.classList.remove("has-hot"); hideTip(); };
    c.addEventListener("pointerenter", on); c.addEventListener("pointermove", on); c.addEventListener("pointerleave", off);
    c.addEventListener("focus", on); c.addEventListener("blur", off);
  });
  reveal(el);
}
