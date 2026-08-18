// Czysta logika wyszukiwarki bazy ćwiczeń w edytorze planu (bez DOM —
// testowana w Node, patrz scripts/test-exercise-picker.mjs).
//
// Baza trenera liczy setki pozycji, więc o czasie pracy decydują trzy
// rzeczy, i wszystkie trzy są tutaj:
// * skrót „ostatnio używane” — pokazywany TYLKO wtedy, gdy nic nie jest
//   wpisane ani odfiltrowane (inaczej zasłaniałby wynik wyszukiwania),
//   i tylko wtedy, gdy w ogóle jest co pokazać (żadnych pustych ramek);
// * nawigacja klawiaturą — strzałki chodzą po wynikach z zawijaniem,
//   żeby dało się dodać serię ćwiczeń bez odrywania rąk od klawiatury;
// * komunikat, który mówi wprost, ile jeszcze zostało i co zrobić przy
//   zerze trafień — zamiast samego „brak wyników”.

// Moduł jest ŚWIADOMIE bez zależności (stan filtrów wchodzi jako zwykłe
// `hasFilters`) — dzięki temu logikę da się uruchomić w Node bez budowania
// całego frontendu, dokładnie jak `ocrUtils.ts`.

/** Czy pokazać skrót „ostatnio używane”. */
export function showRecent(hasFilters: boolean, recentCount: number): boolean {
  return recentCount > 0 && !hasFilters;
}

/** Następny podświetlony wynik przy strzałce (delta -1 / +1).
 *
 * Zawijamy na obu końcach: lista bywa dłuższa niż ekran, a trener nie ma
 * czasu sprawdzać, czy jest już na końcu. Brak wyników = brak
 * podświetlenia (-1). */
export function nextActiveIndex(current: number, delta: number, count: number): number {
  if (count <= 0) return -1;
  if (current < 0) return delta > 0 ? 0 : count - 1;
  return (((current + delta) % count) + count) % count;
}

/** Roving tabindex: fokus trzyma dokładnie jeden wynik (wzorzec z Tabs). */
export function tabIndexFor(index: number, active: number): 0 | -1 {
  if (active < 0) return index === 0 ? 0 : -1;
  return index === active ? 0 : -1;
}

export interface PickerState {
  loading: boolean;
  error: string | null;
  total: number;
  shown: number;
  hasMore: boolean;
  /** Czy jakikolwiek filtr/fraza są ustawione (`hasActiveFilters`). */
  hasFilters: boolean;
}

/** Komunikat listy wyników (aria-live). Przy dużym katalogu mówi, ILE
 * jeszcze zostało; przy zerze trafień podpowiada konkretne wyjście —
 * wyczyszczenie filtrów albo wpisanie nazwy ręcznie. */
export function resultsMessage(state: PickerState): string {
  if (state.error) return "";
  if (state.loading) return "Wyszukiwanie…";
  if (state.total === 0) {
    return state.hasFilters
      ? "Brak ćwiczeń pasujących do wyszukiwania. Wyczyść filtry albo wpisz "
        + "nazwę ćwiczenia ręcznie w polu pozycji."
      : "Twoja baza ćwiczeń jest pusta. Dodaj ćwiczenia w zakładce Wiedza "
        + "albo wpisz nazwę pozycji ręcznie.";
  }
  if (state.hasMore) {
    const left = Math.max(0, state.total - state.shown);
    return `Znaleziono ${state.total} — pokazano ${state.shown}, zostało ${left}. `
      + "Zawęź wyszukiwanie albo pokaż więcej.";
  }
  return `Znaleziono ${state.total} — pokazano wszystkie.`;
}

/** Podpowiedź obsługi klawiaturą (pokazywana pod polem wyszukiwania). */
export const KEYBOARD_HINT =
  "Strzałki góra/dół przechodzą po wynikach, Enter dodaje, Escape zamyka.";
