/**
 * Sprzężone suwaki celów cardio (0.73.0): trzy wagi w procentach, suma
 * zawsze 100. Przesunięcie jednego suwaka zabiera pozostałym proporcjonalnie
 * do ich bieżących wag (przy równych — po równo); suwak zablokowany (kłódka)
 * nie oddaje i nie przyjmuje. Wartości zaokrąglane do 5 %, reszta domykana
 * na największym nieblokowanym suwaku, żeby suma nigdy nie odjechała.
 *
 * Czysta funkcja bez React — testowana w `scripts/test-suwaki.mjs`.
 * Model: `docs/zlecenia/model-suwakow-cardio.md` §3 (simpleks).
 */

export const KROK = 5;

function do5(x: number): number {
  return Math.round(x / KROK) * KROK;
}

/** Nowe wagi po ustawieniu suwaka `indeks` na `nowa` (0–100). */
export function przesun(wagi: number[], indeks: number, nowa: number, zablokowane: boolean[] = []): number[] {
  const n = wagi.length;
  if (n === 0) return [];
  if (indeks < 0 || indeks >= n || zablokowane[indeks]) return [...wagi];
  const zablokowaneSuma = wagi.reduce((s, w, i) => (i !== indeks && zablokowane[i] ? s + w : s), 0);
  const wolne = wagi.map((_, i) => i !== indeks && !zablokowane[i]);
  const maks = 100 - zablokowaneSuma;
  const cel = Math.max(0, Math.min(maks, do5(nowa)));
  if (!wolne.some(Boolean)) {
    // Jedyny wolny suwak: jego wartość wynika z reszty, nie da się go przesunąć.
    return [...wagi];
  }
  const reszta = maks - cel;
  const wolneSuma = wagi.reduce((s, w, i) => (wolne[i] ? s + w : s), 0);
  const liczbaWolnych = wolne.filter(Boolean).length;
  const out = wagi.map((w, i) => {
    if (i === indeks) return cel;
    if (!wolne[i]) return w;
    // Proporcjonalnie do bieżących wag; gdy wolne mają razem 0 — po równo.
    const udzial = wolneSuma > 0 ? w / wolneSuma : 1 / liczbaWolnych;
    return do5(reszta * udzial);
  });
  // Domknięcie sumy do 100 na największym wolnym suwaku (błąd zaokrągleń).
  const suma = out.reduce((s, w) => s + w, 0);
  if (suma !== 100) {
    let j = -1;
    out.forEach((w, i) => { if (wolne[i] && (j < 0 || w > out[j])) j = i; });
    if (j >= 0) out[j] = Math.max(0, out[j] + (100 - suma));
  }
  return out;
}

/** Wagi 0–100 → obiekt dla API (ułamki 0–1, suma 1). */
export function naGoalMix(wagi: number[]): { redukcja: number; wydolnosc: number; regeneracja: number } {
  const [r, w, g] = wagi;
  return { redukcja: r / 100, wydolnosc: w / 100, regeneracja: g / 100 };
}

/** Domyślne wagi (suma 100, krok 5) — te same w panelu trenera i przy braku wag. */
export const WAGI_DOMYSLNE: number[] = [35, 35, 30];

/** Odwrotność: wagi z planu → procenty do pasków/odczytu. */
export function zGoalMix(mix: { redukcja?: number; wydolnosc?: number; regeneracja?: number } | null | undefined): number[] {
  if (!mix || typeof mix.redukcja !== "number" || typeof mix.wydolnosc !== "number") return [...WAGI_DOMYSLNE];
  const r = Math.round(mix.redukcja * 100);
  const w = Math.round(mix.wydolnosc * 100);
  return [r, w, Math.max(0, 100 - r - w)];
}

/** Tekst dla `aria-valuetext` — „Redukcja 50 %”. */
export function opisWagi(etykieta: string, wartosc: number): string {
  return `${etykieta} ${wartosc} %`;
}
