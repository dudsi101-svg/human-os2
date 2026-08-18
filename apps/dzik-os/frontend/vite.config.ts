import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev: proxy /api do backendu FastAPI (port 8000).
// Prod: frontend budowany do dist/ i serwowany przez backend (main.py).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.DZIK_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // Zero inline'owania małych assetów jako data: URI — CSP jest celowo
    // wąska (font-src 'self', bez data:), a Vite domyślnie inline'uje
    // pliki <4KB (np. najmniejsze subsety fontów @fontsource), co łamało
    // politykę. Wszystkie assety trafiają jako hashowane pliki do /assets.
    assetsInlineLimit: 0,
  },
});
