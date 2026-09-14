/**
 * Nazwy ćwiczeń i adresy kart w Wiedzy (0.75.0).
 *
 * Pozycja planu bez `exercise_id` ma tylko nazwę. Serwer dopasowuje ją do
 * bazy trenera po tym samym kluczu, którym import rozpoznaje duplikaty
 * (`import_exercises.normalize_name`: bez wielkości liter, polskich znaków
 * i nadmiarowych spacji). Ten plik trzyma kopię tej normalizacji po stronie
 * przeglądarki — WYŁĄCZNIE jako klucz pamięci podręcznej (dwie pozycje
 * „Przysiad ze sztangą” i „przysiad ze sztanga” to jedno żądanie). O tym,
 * czy dopasowanie istnieje, decyduje serwer; przeglądarka niczego nie
 * zgaduje.
 */

/** Klucz porównania nazwy — lustro `normalize_name` z backendu. */
export function normalizujNazwe(nazwa: string): string {
  const male = nazwa.toLowerCase().replace(/ł/g, "l");
  const bezZnakow = male.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  return bezZnakow.split(/\s+/).filter(Boolean).join(" ");
}

/** Klucz pamięci podręcznej opisu: po identyfikatorze, gdy jest; inaczej po nazwie. */
export function kluczOpisu(exerciseId: string | null | undefined, nazwa: string): string {
  if (exerciseId) return `id:${exerciseId}`;
  return `nazwa:${normalizujNazwe(nazwa)}`;
}

export type RolaOpisu = "klient" | "trener";

/** Adres API karty ćwiczenia dla danej roli — po id albo po nazwie. */
export function adresApiOpisu(rola: RolaOpisu, exerciseId: string | null | undefined, nazwa: string): string {
  const baza = rola === "trener" ? "/api/coach/exercises" : "/api/me/exercises";
  if (exerciseId) return `${baza}/${encodeURIComponent(exerciseId)}`;
  return `${baza}/by-name?name=${encodeURIComponent(nazwa.trim())}`;
}

/**
 * Powrót z karty w Wiedzy: tylko wewnętrzna ścieżka aplikacji („/plan”,
 * „/trener/klient/…”). Wszystko inne (pusty, „//zly.host”, „http:…”) daje
 * `null` — wtedy karta pokazuje zwykłe „Wróć do Wiedzy”.
 */
export function bezpiecznyPowrot(wartosc: string | null | undefined): string | null {
  if (!wartosc) return null;
  if (!wartosc.startsWith("/") || wartosc.startsWith("//") || wartosc.startsWith("/\\")) return null;
  if (/[\s<>"']/.test(wartosc)) return null;
  return wartosc;
}

/** Adres karty ćwiczenia w Wiedzy (klient: `/wiedza`, trener: `/trener/wiedza`). */
export function adresKartyCwiczenia(rola: RolaOpisu, exerciseId: string, powrot?: string | null): string {
  const p = new URLSearchParams();
  if (rola === "klient") p.set("czesc", "training");
  p.set("cwiczenie", exerciseId);
  const wroc = bezpiecznyPowrot(powrot);
  if (wroc) p.set("powrot", wroc);
  return `${rola === "trener" ? "/trener/wiedza" : "/wiedza"}?${p.toString()}`;
}

/** Etykieta przycisku powrotu z karty: skąd klient przyszedł. */
export function etykietaPowrotu(powrot: string | null): string {
  if (!powrot) return "Wróć do Wiedzy";
  if (powrot === "/plan") return "Wróć do planu";
  if (powrot === "/") return "Wróć na Dzisiaj";
  if (powrot.startsWith("/trener/klient/")) return "Wróć do karty klienta";
  if (powrot.startsWith("/trener/szablony")) return "Wróć do szablonów";
  return "Wróć";
}
