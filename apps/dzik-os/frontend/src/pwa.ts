// Rejestracja service workera + wykrywanie nowej wersji aplikacji.
// Domyślne zachowanie przeglądarki (cichy skipWaiting) potrafi podmienić
// kod pod użytkownikiem w trakcie sesji — tu zamiast tego nowa wersja
// czeka, aż użytkownik świadomie potwierdzi odświeżenie (UpdateBanner).

type UpdateListener = () => void;

let waitingWorker: ServiceWorker | null = null;
const listeners: UpdateListener[] = [];

function notify() {
  listeners.forEach((cb) => cb());
}

export function onUpdateAvailable(cb: UpdateListener): () => void {
  listeners.push(cb);
  return () => {
    const i = listeners.indexOf(cb);
    if (i >= 0) listeners.splice(i, 1);
  };
}

export function registerServiceWorker() {
  if (!("serviceWorker" in navigator) || import.meta.env.DEV) return;

  window.addEventListener("load", async () => {
    try {
      const reg = await navigator.serviceWorker.register("/sw.js");
      if (reg.waiting && navigator.serviceWorker.controller) {
        waitingWorker = reg.waiting;
        notify();
      }
      reg.addEventListener("updatefound", () => {
        const fresh = reg.installing;
        if (!fresh) return;
        fresh.addEventListener("statechange", () => {
          if (fresh.state === "installed" && navigator.serviceWorker.controller) {
            waitingWorker = fresh;
            notify();
          }
        });
      });
    } catch {
      // Brak service workera nie blokuje działania aplikacji.
    }
  });

  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    // Przeładowujemy WYŁĄCZNIE po świadomym kliknięciu użytkownika
    // w baner aktualizacji. Przy pierwszej wizycie świeżo zainstalowany
    // worker przejmuje kontrolę sam (clients.claim) — przeładowanie w tym
    // momencie kasowałoby wypełniony formularz (np. logowanie w trakcie),
    // a użytkownik o żadną aktualizację nie prosił.
    if (!updateRequested || reloading) return;
    reloading = true;
    window.location.reload();
  });
}

/** Czy użytkownik potwierdził odświeżenie do nowej wersji (baner). */
let updateRequested = false;

export function applyUpdate() {
  updateRequested = true;
  waitingWorker?.postMessage({ type: "SKIP_WAITING" });
}
