// Czysta logika serii czasowych do wykresów (bez DOM — testowana w Node,
// patrz scripts/test-series-utils.mjs).
//
// Zasada jakości danych (PROMPT 11 pkt 16): brakujące pomiary NIE są
// interpolowane jako rzeczywiste dane. Gdy między kolejnymi punktami serii
// o znanym rytmie (dziennym/tygodniowym) jest dziura większa niż rytm,
// wstawiamy punkt-przerwę (value: null) — Sparkline rysuje wtedy przerwę
// w linii zamiast łączyć przez dziurę.

export interface DatedPoint {
  /** Data kalendarzowa YYYY-MM-DD. */
  date: string;
  value: number;
}

export interface GappedPoint {
  /** null = syntetyczny punkt-przerwa (brak danych, nie pomiar). */
  date: string | null;
  value: number | null;
}

/** Liczba dni między dwiema datami YYYY-MM-DD (UTC — bez wpływu strefy
 * przeglądarki na daty kalendarzowe). Nieparsowalna data => NaN. */
export function daysBetween(a: string, b: string): number {
  const parse = (s: string): number => {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s);
    if (!m) return Number.NaN;
    return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  };
  return (parse(b) - parse(a)) / 86_400_000;
}

/**
 * Wstawia punkty-przerwy do serii o oczekiwanym rytmie `intervalDays`
 * (1 = dziennik dzienny, 7 = raporty tygodniowe). Przerwa powstaje, gdy
 * odstęp między kolejnymi punktami przekracza 1,5 × rytm (tolerancja na
 * drobne przesunięcia daty). Nieparsowalne daty nie generują przerwy —
 * lepiej pokazać ciągłą linię niż wywrócić wykres na danych historycznych.
 */
export function withGaps(points: DatedPoint[], intervalDays: number): GappedPoint[] {
  const out: GappedPoint[] = [];
  for (let i = 0; i < points.length; i++) {
    if (i > 0) {
      const gap = daysBetween(points[i - 1].date, points[i].date);
      if (Number.isFinite(gap) && gap > intervalDays * 1.5) {
        out.push({ date: null, value: null });
      }
    }
    out.push(points[i]);
  }
  return out;
}
