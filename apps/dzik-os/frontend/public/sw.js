/* Dzik OS — service worker (PWA).
   Strategia: nawigacje network-first (świeża aplikacja przy każdym
   otwarciu; cache tylko jako fallback offline), statyki cache-first,
   network-only dla /api (dane zdrowotne nigdy nie są cachowane). */
const CACHE = "dzik-os-v2";
const APP_SHELL = [
  "/", "/manifest.webmanifest",
  "/icons/favicon-64.png", "/icons/boar-mark.png", "/icons/logo-full.png",
];

self.addEventListener("install", (event) => {
  // Celowo BEZ self.skipWaiting() — nowa wersja czeka, aż użytkownik
  // świadomie potwierdzi odświeżenie (patrz src/pwa.ts + UpdateBanner),
  // zamiast cicho podmieniać kod aplikacji pod ręką w trakcie sesji.
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(APP_SHELL)));
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || url.pathname.startsWith("/api")) {
    return; // API zawsze z sieci — bez cache
  }
  if (event.request.mode === "navigate") {
    // Network-first: otwarcie/odświeżenie aplikacji zawsze próbuje
    // pobrać świeżą wersję (to naturalny moment aktualizacji — nie jest
    // to cicha podmiana kodu w trakcie sesji); cache tylko offline.
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone();
            caches.open(CACHE).then((c) => c.put("/", clone));
          }
          return resp;
        })
        .catch(() => caches.match("/"))
    );
    return;
  }
  event.respondWith(
    caches.match(event.request).then(
      (cached) =>
        cached ||
        fetch(event.request)
          .then((resp) => {
            if (resp.ok && url.origin === self.location.origin) {
              const clone = resp.clone();
              caches.open(CACHE).then((c) => c.put(event.request, clone));
            }
            return resp;
          })
          .catch(() => caches.match("/"))
    )
  );
});
