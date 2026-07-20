/* Knead service worker.
   Network-first for code (so deploys show up immediately, offline falls back
   to cache); cache-first for fonts/icons (rarely change, want them instant). */
var CACHE = "knead-v3";
var ASSETS = [
  ".", "index.html", "styles.css", "glyphs.js", "app.js", "about.html",
  "manifest.webmanifest",
  "fonts/serif.woff2", "fonts/sans.woff2", "fonts/mono.woff2",
  "fonts/display.woff2", "fonts/blackletter.woff2", "fonts/pixel.woff2",
  "apple-touch-icon.png", "icon-192.png", "icon-512.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) {
    return Promise.all(ASSETS.map(function (a) {
      return c.add(a).catch(function () {});   // tolerate any one miss
    }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function isCode(req) {
  if (req.mode === "navigate") return true;
  return /\.(html|js|css|webmanifest)(\?|$)/.test(req.url);
}

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  if (isCode(e.request)) {
    // network-first: always try for the freshest code, fall back to cache offline
    e.respondWith(
      fetch(e.request).then(function (res) {
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return res;
      }).catch(function () {
        return caches.match(e.request).then(function (hit) { return hit || caches.match("index.html"); });
      })
    );
  } else {
    // cache-first for fonts/icons
    e.respondWith(
      caches.match(e.request).then(function (hit) {
        return hit || fetch(e.request).then(function (res) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
          return res;
        });
      })
    );
  }
});

