/** Filtry bazy ćwiczeń — czysta logika budowania zapytania do API.
 *
 * Wyszukiwanie i filtrowanie liczy SERWER (baza ma ponad 150 pozycji, a
 * dopasowanie musi być odporne na polskie znaki tak samo w każdym
 * widoku). Tu składamy tylko parametry — bez żadnej filtrującej logiki
 * po stronie przeglądarki, żeby oba widoki (klient i trener) pytały
 * dokładnie tak samo. */

export interface ExerciseFilters {
  q: string;
  muscle: string;
  equipment: string;
  level: string;
  pattern: string;
}

export const EMPTY_FILTERS: ExerciseFilters = {
  q: "", muscle: "", equipment: "", level: "", pattern: "",
};

/** Najczęstszy sprzęt — podpowiedzi do pola tekstowego (filtr działa na
 * fragmencie nazwy, więc lista nie musi być kompletna). */
export const EQUIPMENT_SUGGESTIONS = [
  "Sztanga", "Hantle", "Kettlebell", "Wyciąg", "Maszyna", "Guma", "Drążek",
  "Ławka", "Mata", "Brak",
];

/** Buduje query string do /api/me/exercises i /api/coach/exercises.
 * Puste filtry są pomijane (żadnych pustych parametrów w URL). */
export function exerciseQuery(
  filters: Partial<ExerciseFilters>,
  offset = 0,
  limit = 30,
  extra: Record<string, string> = {},
): string {
  const params = new URLSearchParams();
  const entries: [string, string | undefined][] = [
    ["q", filters.q],
    ["muscle", filters.muscle],
    ["equipment", filters.equipment],
    ["level", filters.level],
    ["pattern", filters.pattern],
  ];
  for (const [key, value] of entries) {
    const trimmed = (value ?? "").trim();
    if (trimmed) params.set(key, trimmed);
  }
  for (const [key, value] of Object.entries(extra)) {
    if (value) params.set(key, value);
  }
  params.set("limit", String(limit));
  if (offset > 0) params.set("offset", String(offset));
  return params.toString();
}

/** Czy jakikolwiek filtr jest aktywny (do pokazania „wyczyść”). */
export function hasActiveFilters(filters: ExerciseFilters): boolean {
  return Object.values(filters).some((v) => v.trim() !== "");
}
