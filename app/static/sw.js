// Roundbreak Career service worker.
//
// HTTPS is required for browsers to register a service worker from
// a non-localhost origin. Over plain LAN HTTP it simply won't activate
// — the app continues to work, but no offline caching.
//
// Strategy:
//   - On install: cache the app shell.
//   - HTML (GET, same-origin): stale-while-revalidate.
//   - Vault renders (/vault/*): cache on view, network first when online.
//   - Static assets: cache-first.
//   - Never cache POST/PUT/DELETE or auth-sensitive endpoints.

const CACHE = "roundbreak-v1";
const SHELL = [
  "/",
  "/static/css/main.css",
  "/static/js/app.js",
  "/static/js/kanban.js",
  "/static/js/practice.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

const NEVER_CACHE = ["/login", "/logout", "/backup", "/backups"];

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (NEVER_CACHE.some((p) => url.pathname.startsWith(p))) return;

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((resp) => {
        const clone = resp.clone();
        caches.open(CACHE).then((c) => c.put(req, clone));
        return resp;
      }))
    );
    return;
  }

  // HTML and vault renders: stale-while-revalidate.
  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req);
      const networkPromise = fetch(req)
        .then((resp) => {
          if (resp && resp.status === 200) cache.put(req, resp.clone());
          return resp;
        })
        .catch(() => cached);
      return cached || networkPromise;
    })
  );
});
