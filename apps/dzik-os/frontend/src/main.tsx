// Fonty self-hostowane (@fontsource) — te same rodziny i wagi, które
// wcześniej ładował <link> do Google Fonts (patrz styles.css:
// --font-display: Unbounded 600/700/800, --font-body: Inter 400–800).
// Dzięki temu CSP może zostać przy font-src 'self', a IP użytkowników
// nie jest wysyłane do Google.
//
// Importowane są PEŁNE pliki wagi (a nie pojedyncze subsety), bo tylko one
// niosą `unicode-range`. To on decyduje, że przeglądarka pobierze wyłącznie
// subset potrzebny dla wyświetlanego tekstu — dla polszczyzny `latin`
// i `latin-ext`, nigdy cyrylicę czy grekę. Importy per-subset (`latin-600.css`)
// nie mają `unicode-range`, więc drugi @font-face tej samej wagi nadpisywałby
// pierwszy i zostawałby tylko jeden subset.
//
// Nadmiarowe subsety były problemem WYŁĄCZNIE w precache service workera,
// który instalował je na urządzenie bez pytania o zasięg znaków — i tam są
// odfiltrowane (scripts/inject-precache.mjs).
import "@fontsource/unbounded/600.css";
import "@fontsource/unbounded/700.css";
import "@fontsource/unbounded/800.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/800.css";
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { reportFrontendError } from "./api";
import App from "./App";
import { ErrorBoundary, OfflineScreen, UpdateBanner } from "./components";
import { registerServiceWorker } from "./pwa";
import "./styles.css";

// Nieprzechwycone błędy JS i odrzucone Promise — raportowane do backendu
// w formie zredagowanej (typ + pliki własne, bez treści danych; limit
// kliencki i serwerowy, patrz api.reportFrontendError).
window.addEventListener("error", (e) => {
  reportFrontendError(e.error ?? e.message, "window:onerror");
});
window.addEventListener("unhandledrejection", (e) => {
  reportFrontendError(e.reason, "window:unhandledrejection");
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <UpdateBanner />
    <OfflineScreen />
    {/* Globalna granica błędów — awaria renderowania nie zostawia białego
        ekranu; granica per trasa jest w App.tsx. */}
    <ErrorBoundary scope="app">
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);

registerServiceWorker();
