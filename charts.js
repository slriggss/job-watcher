// Tiny inline-SVG charts (no external library, so they also work offline).
const SVG_W = 720, SVG_H = 280, PAD = { l: 44, r: 12, t: 12, b: 44 };
const COLORS = ["var(--accent)", "var(--accent2)"];

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
  return s;
}

// series: [{name, values}] sharing one list of labels
function lineChart(el, labels, series) {
  const n = labels.length, max = niceMax(Math.max(1, ...series.flatMap(s => s.values)));
  const x = i => PAD.l + (n === 1 ? (SVG_W - PAD.l - PAD.r) / 2 : (i * (SVG_W - PAD.l - PAD.r)) / (n - 1));
  const y = v => PAD.t + (SVG_H - PAD.t - PAD.b) * (1 - v / max);
  let s = frame(max);
  const step = Math.max(1, Math.ceil(n / 8));
  labels.forEach((l, i) => { if (i % step === 0 || i === n - 1) s += `<text x="${x(i)}" y="${SVG_H - PAD.b + 16}" text-anchor="middle">${l.slice(5)}</text>`; });
  series.forEach((se, k) => {
    const pts = se.values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
    s += `<polyline fill="none" stroke="${COLORS[k % 2]}" stroke-width="2.5" points="${pts}"/>` +
         se.values.map((v, i) => `<circle cx="${x(i)}" cy="${y(v)}" r="3.5" fill="${COLORS[k % 2]}"><title>${labels[i]} · ${se.name}: ${v}</title></circle>`).join("");
  });
  const legend = series.map((se, k) => `<tspan fill="${COLORS[k % 2]}">● </tspan>${se.name}   `).join("");
  s += `<text x="${PAD.l}" y="${SVG_H - 6}">${legend}</text>`;
  el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" width="100%">${s}</svg>`;
}

function barChart(el, labels, values, name) {
  const n = labels.length, max = niceMax(Math.max(1, ...values));
  const w = (SVG_W - PAD.l - PAD.r) / n, y = v => PAD.t + (SVG_H - PAD.t - PAD.b) * (1 - v / max);
  let s = frame(max);
  const step = Math.max(1, Math.ceil(n / 24));
  labels.forEach((l, i) => {
    const bx = PAD.l + i * w + w * 0.15;
    s += `<rect x="${bx}" y="${y(values[i])}" width="${w * 0.7}" height="${SVG_H - PAD.b - y(values[i])}" fill="var(--accent)"><title>${l}: ${values[i].toLocaleString()} ${name}</title></rect>`;
    if (i % step === 0) {
      const short = l.length > 14 ? l.slice(0, 13) + "…" : (/^\d{4}-/.test(l) ? l.slice(5) : l);
      s += `<text x="${bx + w * 0.35}" y="${SVG_H - PAD.b + 14}" text-anchor="end" transform="rotate(-35 ${bx + w * 0.35} ${SVG_H - PAD.b + 14})">${short}</text>`;
    }
  });
  el.innerHTML = `<svg viewBox="0 0 ${SVG_W} ${SVG_H}" role="img" width="100%">${s}</svg>`;
}
