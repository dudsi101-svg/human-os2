import { expect, test } from "@playwright/test";

/**
 * Zasoby, bez których PWA nie jest PWA. Nie wymagają logowania, więc to
 * najtańsza możliwa bramka — a mimo to wyłapują realną klasę awarii:
 * błąd konfiguracji serwowania `dist/` przez backend, przez który
 * aplikacja instaluje się „pusta" albo przestaje działać offline.
 *
 * Przeniesione z `apps/dzik-os/e2e/test_e2e_browser.py`, który dublował
 * testy logowania z `logowanie.spec.ts` i — jak cały tamten katalog — nie
 * chodził w żadnym przebiegu CI.
 */

test("manifest PWA i service worker są serwowane", async ({ request }) => {
  const manifest = await request.get("/manifest.webmanifest");
  expect(manifest.status()).toBe(200);
  expect(await manifest.text()).toContain('"Dzik OS');

  const sw = await request.get("/sw.js");
  expect(sw.status()).toBe(200);
  // Lista precache jest wstrzykiwana przy buildzie (inject-precache.mjs).
  // Jej brak oznacza service workera bez trybu offline — awaria cicha,
  // bo aplikacja online zachowuje się wtedy normalnie.
  expect(await sw.text()).toContain("self.__PRECACHE_MANIFEST");
});
