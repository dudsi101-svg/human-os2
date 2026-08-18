/* Dzik OS — service worker (PWA).

   Strategie (patrz też docs w repo aplikacji):
   - /api/*           → network-only. Dane zdrowotne NIGDY nie trafiają do
                        Cache Storage — fetch handler w ogóle nie przejmuje
                        tych żądań, a activate() wymiata ewentualne stare
                        wpisy z poprzednich wersji cache.
   - nawigacje        → network-first (świeża aplikacja przy każdym
                        otwarciu); offline: precache'owany shell
                        (/index.html) z bieżącego builda.
   - statyki wersji   → cache-first z precache generowanego przy buildzie
                        (scripts/inject-precache.mjs wstrzykuje do dist/sw.js
                        pełną listę zahaszowanych plików + wersję builda).
   - brakujący asset  → błąd sieci, NIGDY index.html (żaden skrypt/styl/
                        obrazek nie dostanie HTML — to dawało błąd MIME
                        i pusty ekran).
   - cross-origin (np. Google Fonts) → nieprzejmowane; offline działa
                        fallback systemowych fontów.

   Aktualizacje: celowo BEZ auto-skipWaiting przy instalacji — nowa wersja
   czeka, aż użytkownik świadomie potwierdzi odświeżenie (src/pwa.ts +
   UpdateBanner). Przeładowanie następuje TYLKO po kliknięciu użytkownika. */

// Wstrzykiwane przez scripts/inject-precache.mjs na początku dist/sw.js:
//   self.__BUILD_VERSION  — hash zawartości builda (wersjonowanie cache),
//   self.__PRECACHE_MANIFEST — pełna lista plików tej wersji.
// Fallback poniżej działa tylko poza buildem produkcyjnym (dev/test).
const VERSION = self.__BUILD_VERSION || "dev";
const PRECACHE_URLS = Array.isArray(self.__PRECACHE_MANIFEST)
  ? self.__PRECACHE_MANIFEST
  : ["/index.html", "/manifest.webmanifest"];
const PRECACHE = `dzik-os-precache-${VERSION}`;
const SHELL_URL = "/index.html";

self.addEventListener("install", (event) => {
  // Celowo BEZ auto-skipWaiting — patrz komentarz na górze pliku.
  event.waitUntil(
    caches.open(PRECACHE).then((cache) =>
      cache.addAll(
        // cache: "reload" — omija HTTP cache przeglądarki, żeby precache
        // zawierał dokładnie bajty tej wersji z serwera.
        PRECACHE_URLS.map((url) => new Request(url, { cache: "reload" }))
      )
    )
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting();
});

// Web Push — treść przychodzi z backendu (nigdy dane zdrowotne,
// tylko neutralne wezwanie do wejścia do aplikacji).
self.addEventListener("push", (event) => {
  let data = { title: "Dzik OS", body: "", url: "/" };
  try {
    data = { ...data, ...event.data.json() };
  } catch {
    /* pusty payload */
  }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: { url: data.url },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      for (const win of wins) {
        if ("focus" in win) {
          win.navigate(url);
          return win.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // 1) Wersjonowanie: usuń wszystkie cache poprzednich buildów
      //    (w tym stare "dzik-os-v*" sprzed precache'u per build).
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => k !== PRECACHE).map((k) => caches.delete(k))
      );
      // 2) Higiena danych: defensywnie wymieć z bieżącego cache wszystko,
      //    co wygląda na /api (nie powinno się nigdy pojawić — fetch
      //    handler nie dotyka /api — ale dane zdrowotne uzasadniają pas
      //    i szelki).
      const cache = await caches.open(PRECACHE);
      for (const req of await cache.keys()) {
        if (new URL(req.url).pathname.startsWith("/api")) {
          await cache.delete(req);
        }
      }
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return; // mutacje zawsze do sieci
  if (url.origin !== self.location.origin) return; // np. Google Fonts
  if (url.pathname.startsWith("/api")) {
    return; // API network-only — dane zdrowotne/pliki prywatne bez cache
  }
  if (event.request.mode === "navigate") {
    // Network-first: otwarcie/odświeżenie aplikacji zawsze próbuje pobrać
    // świeżą wersję (naturalny moment aktualizacji — nie jest to cicha
    // podmiana kodu w trakcie sesji). Offline: shell z precache tej
    // wersji, którego assety też są w precache — spójny zestaw.
    event.respondWith(
      fetch(event.request).catch(() =>
        caches.open(PRECACHE).then((cache) => cache.match(SHELL_URL))
      )
    );
    return;
  }
  // Statyki: cache-first z precache; brak w cache → sieć. Gdy i sieć
  // zawiedzie, odpowiedzią jest błąd sieci — NIGDY fallback do HTML
  // (HTML zamiast JS/CSS = błąd MIME i pusty ekran).
  event.respondWith(
    caches
      .open(PRECACHE)
      .then((cache) => cache.match(event.request))
      .then((cached) => cached || fetch(event.request))
  );
});
