// Czysta logika bazy produktów spożywczych (bez DOM — testowana w Node,
// patrz scripts/test-food-utils.mjs). Ten sam kalkulator porcji obsługuje
// panel trenera i panel klienta, żeby liczby nigdy się nie rozjechały
// między widokami.
//
// Zasada uczciwości danych (runda 0.22.0): wartości odżywcze są uśrednione
// i przybliżone. Tekst `FOOD_APPROXIMATION_HINT` towarzyszy katalogowi i
// kalkulatorowi w interfejsie; backend niesie własny `disclaimer` w każdej
// odpowiedzi API i to on jest źródłem prawdy, gdy jest dostępny.

export const FOOD_APPROXIMATION_HINT =
  "Wartości odżywcze są przybliżone i uśrednione — realne zależą od marki, " +
  "partii, obróbki i sposobu przygotowania. Traktuj je jako punkt wyjścia " +
  "do oszacowania, nie jako pomiar.";

/** Produkt w zakresie potrzebnym do przeliczeń (podzbiór FoodProductRow). */
export interface PortionSource {
  kcal_100g: number;
  protein_100g: number;
  fat_100g: number;
  carbs_100g: number;
  fiber_100g?: number | null;
  default_portion_g?: number | null;
  unit_name?: string | null;
  unit_grams?: number | null;
}

export interface PortionValues {
  grams: number;
  kcal: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  /** null = produkt nie ma zadeklarowanego błonnika (brak danych, nie zero). */
  fiber_g: number | null;
}

const PL_MAP: Record<string, string> = {
  ą: "a", ć: "c", ę: "e", ł: "l", ń: "n", ó: "o", ś: "s", ż: "z", ź: "z",
};

/** Nazwa sprowadzona do postaci porównywalnej: małe litery, bez polskich
 * znaków diakrytycznych. Ta sama reguła co w backendzie — dzięki temu
 * podpowiedzi w UI i wyniki z API zgadzają się co do dopasowania. */
export function normalizeFoodName(text: string): string {
  const lowered = text.trim().toLowerCase().replace(/[ąćęłńóśżź]/g, (c) => PL_MAP[c] ?? c);
  return lowered.normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
}

/** Czy nazwa produktu pasuje do zapytania (dopasowanie ścisłe). */
export function matchesFoodQuery(name: string, query: string): boolean {
  const needle = normalizeFoodName(query);
  return needle === "" || normalizeFoodName(name).includes(needle);
}

/** Zaokrąglenie makro do 0,1 g — więcej miejsc po przecinku sugerowałoby
 * precyzję, której te dane nie mają. */
export function roundMacro(value: number): number {
  return Math.round(value * 10) / 10;
}

/** Gramatura porcji: z liczby sztuk (gdy produkt ma jednostkę) albo wprost. */
export function unitsToGrams(product: PortionSource, units: number): number | null {
  if (!product.unit_grams || product.unit_grams <= 0) return null;
  if (!Number.isFinite(units) || units < 0) return null;
  return roundMacro(units * product.unit_grams);
}

/** Ile sztuk odpowiada danej gramaturze (do podpowiedzi „≈ 2 kromki”). */
export function gramsToUnits(product: PortionSource, grams: number): number | null {
  if (!product.unit_grams || product.unit_grams <= 0) return null;
  if (!Number.isFinite(grams) || grams <= 0) return null;
  return roundMacro(grams / product.unit_grams);
}

/** Przeliczenie porcji na kalorie i makro. Ujemne/niepoprawne wejście
 * traktujemy jako 0 g — kalkulator nigdy nie pokazuje NaN. */
export function computePortion(product: PortionSource, grams: number): PortionValues {
  const safe = Number.isFinite(grams) && grams > 0 ? grams : 0;
  const factor = safe / 100;
  return {
    grams: roundMacro(safe),
    kcal: Math.round(product.kcal_100g * factor),
    protein_g: roundMacro(product.protein_100g * factor),
    fat_g: roundMacro(product.fat_100g * factor),
    carbs_g: roundMacro(product.carbs_100g * factor),
    fiber_g:
      product.fiber_100g === null || product.fiber_100g === undefined
        ? null
        : roundMacro(product.fiber_100g * factor),
  };
}

/** Domyślna gramatura w polu porcji: typowa porcja produktu albo 100 g. */
export function defaultPortionGrams(product: PortionSource): number {
  return product.default_portion_g != null && product.default_portion_g > 0
    ? product.default_portion_g
    : 100;
}

/** Podpowiedź jednostki sztukowej, np. „1 kromka ≈ 35 g”. */
export function unitHint(product: PortionSource): string | null {
  if (!product.unit_name || !product.unit_grams) return null;
  return `1 ${product.unit_name} ≈ ${roundMacro(product.unit_grams)} g`;
}

/** Jednowierszowe podsumowanie porcji do wyświetlenia obok pola gramatury. */
export function formatPortion(values: PortionValues): string {
  const parts = [
    `${values.kcal} kcal`,
    `B ${values.protein_g} g`,
    `T ${values.fat_g} g`,
    `W ${values.carbs_g} g`,
  ];
  if (values.fiber_g !== null) parts.push(`Bł ${values.fiber_g} g`);
  return parts.join(" · ");
}
