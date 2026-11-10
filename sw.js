// Network first, so online visits show the latest data; the cache is the offline fallback.
// - The two data files are stored at install, so the very first offline visit already has them.
// - Only page navigations fall back to index.html. A data file that is not cached fails as missing, so the
//   page can say so instead of trying to parse HTML as JSON.
// - A data request waits at most DATA_TIMEOUT_MS for the network, then uses the cached copy if there is one.
const CACHE = "job-watcher-v8";  // bump together with the ?v= on the script and style tags in the three pages
const SHELL = ["./", "index.html", "browse.html", "market.html", "style.css?v=8", "app.js?v=8", "charts.js?v=8",
  "market.js?v=8", "cards.js?v=8", "browse.js?v=8", "facts.js?v=8", "manifest.webmanifest", "icon.svg", "icon-192.png", "icon-512.png",
  "icon-maskable-512.png", "fonts/EBGaramond.woff2", "fonts/Inter.woff2"];
const DATA = ["data/status.json", "data/history.csv"];
const DATA_TIMEOUT_MS = 4000;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(async c => {
    await c.addAll(SHELL);
    await Promise.all(DATA.map(u => c.add(u).catch(() => {})));  // a data file that cannot be fetched now is fetched later
  }));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const isData = url => DATA.some(d => url.pathname.endsWith("/" + d));

function fromNetwork(request, timeoutMs) {
  const ctl = new AbortController(), timer = timeoutMs ? setTimeout(() => ctl.abort(), timeoutMs) : null;
  return fetch(request, timeoutMs ? { signal: ctl.signal } : undefined).finally(() => clearTimeout(timer));
}

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  e.respondWith((async () => {
    try {
      const res = await fromNetwork(e.request, isData(url) ? DATA_TIMEOUT_MS : 0);
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return res;
    } catch (err) {
      const hit = await caches.match(e.request, { ignoreSearch: true });
      if (hit) return hit;
      if (isData(url) && navigator.onLine) return fetch(e.request);  // slow, nothing cached: keep waiting for the network
      if (e.request.mode === "navigate") return caches.match("index.html");
      return Response.error();  // missing offline: the request fails, so the page can report it
    }
  })());
});
