// Fonty self-hostowane (@fontsource) — te same rodziny i wagi, które
// wcześniej ładował <link> do Google Fonts (patrz styles.css:
// --font-display: Unbounded 600/700/800, --font-body: Inter 400–800).
// Dzięki temu CSP może zostać przy font-src 'self', a IP użytkowników
// nie jest wysyłane do Google.
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
import App from "./App";
import { UpdateBanner } from "./components";
import { registerServiceWorker } from "./pwa";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <UpdateBanner />
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);

registerServiceWorker();
