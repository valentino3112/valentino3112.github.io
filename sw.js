/* CEFI2 — service worker : tout le site est mis en cache pour fonctionner hors ligne.
   Stratégie « stale-while-revalidate » : on sert le cache tout de suite et on le met à jour
   en arrière-plan ; une nouvelle version du site apparaît donc au chargement suivant.
   Changer VERSION force un nouveau précache complet. */
var VERSION = "cefi2-v1";
var FILES = [
  "./", "index.html", "cours.html", "formulaire.html", "methodes.html", "exercices.html", "quiz.html", "calculs.html",
  "css/style.css", "js/app.js", "js/exos.js", "js/exos-data.js", "js/quiz.js", "js/quiz-data.js", "js/calc.js",
  "manifest.webmanifest", "icons/icon.svg", "icons/icon-180.png", "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png"
];

self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(VERSION).then(function (c) {
    return c.addAll(FILES.map(function (f) { return new Request(f, { cache: "reload" }); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k.indexOf("cefi2-") === 0 && k !== VERSION; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;
  var scope = new URL(self.registration.scope);
  if (url.pathname.indexOf(scope.pathname + "signal/") === 0) return;   // l'autre site garde son fonctionnement

  e.respondWith(caches.open(VERSION).then(function (cache) {
    return cache.match(req, { ignoreSearch: true }).then(function (hit) {
      var net = fetch(req).then(function (res) {
        if (res && res.ok && res.type === "basic") cache.put(req, res.clone());
        return res;
      }).catch(function () { return null; });
      if (hit) { e.waitUntil(net); return hit; }
      return net.then(function (res) {
        if (res) return res;
        if (req.mode === "navigate") return cache.match("index.html");
        return new Response("Hors ligne", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
      });
    });
  }));
});
