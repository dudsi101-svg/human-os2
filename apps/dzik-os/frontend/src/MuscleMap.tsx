import { MUSCLE_LABELS } from "./types";

/* Rysunek pracujących mięśni — prosty szkic sylwetki (przód i tył) rysowany
 * wektorowo w aplikacji.
 *
 * Dlaczego SVG w kodzie, a nie obrazki: strona ma ścisłą politykę CSP bez
 * zewnętrznych zasobów, aplikacja musi działać offline, a rysunek ma
 * dopasowywać się do motywu i skalować bez utraty ostrości. Cały szkic waży
 * kilkanaście kilobajtów i nie wymaga ani jednego zapytania do sieci.
 *
 * Rysunek jest SCHEMATEM orientacyjnym, nie atlasem anatomicznym: pokazuje
 * OKOLICĘ ciała, która pracuje, żeby podopieczny wiedział „gdzie to czuć".
 * Dlatego pod spodem zawsze jest ta sama informacja słowami — rysunek jej
 * nie zastępuje (czytniki ekranu dostają pełny opis w aria-label). */

type Shape =
  | { r: [number, number, number, number, number?] } // x, y, szer., wys., promień
  | { e: [number, number, number, number] };         // cx, cy, rx, ry

interface Region {
  key: string;
  view: "front" | "back";
  shapes: Shape[];
}

// Układ współrzędnych obu sylwetek: 120 × 300.
const REGIONS: Region[] = [
  // ——— PRZÓD ———
  { key: "CZWOROBOCZNY", view: "front", shapes: [
    { r: [47, 39, 11, 8, 3] }, { r: [62, 39, 11, 8, 3] } ] },
  { key: "BARK_PRZEDNI", view: "front", shapes: [
    { e: [41, 53, 7, 9] }, { e: [79, 53, 7, 9] } ] },
  { key: "BARK_BOCZNY", view: "front", shapes: [
    { e: [34, 54, 5, 9] }, { e: [86, 54, 5, 9] } ] },
  { key: "KLATKA_PIERSIOWA", view: "front", shapes: [
    { r: [46, 57, 13, 21, 5] }, { r: [61, 57, 13, 21, 5] } ] },
  { key: "BICEPS", view: "front", shapes: [
    { r: [31, 70, 9, 25, 4] }, { r: [80, 70, 9, 25, 4] } ] },
  { key: "PRZEDRAMIE", view: "front", shapes: [
    { r: [29, 98, 9, 27, 4] }, { r: [82, 98, 9, 27, 4] } ] },
  { key: "MIESNIE_GLEBOKIE", view: "front", shapes: [
    { r: [49, 92, 22, 30, 8] } ] },
  { key: "BRZUCH_PROSTY", view: "front", shapes: [
    { r: [52, 80, 16, 40, 5] } ] },
  { key: "BRZUCH_SKOSNY", view: "front", shapes: [
    { r: [45, 84, 6, 34, 3] }, { r: [69, 84, 6, 34, 3] } ] },
  { key: "ZGINACZE_BIODRA", view: "front", shapes: [
    { r: [47, 124, 9, 15, 4] }, { r: [64, 124, 9, 15, 4] } ] },
  { key: "ODWODZICIELE", view: "front", shapes: [
    { r: [44, 142, 6, 38, 3] }, { r: [70, 142, 6, 38, 3] } ] },
  { key: "CZWOROGLOWY_UDA", view: "front", shapes: [
    { r: [45, 146, 12, 60, 6] }, { r: [63, 146, 12, 60, 6] } ] },
  { key: "PRZYWODZICIELE", view: "front", shapes: [
    { r: [54, 150, 4, 46, 2] }, { r: [62, 150, 4, 46, 2] } ] },
  { key: "LYDKA", view: "front", shapes: [
    { r: [46, 226, 10, 42, 5] }, { r: [64, 226, 10, 42, 5] } ] },

  // ——— TYŁ ———
  { key: "CZWOROBOCZNY", view: "back", shapes: [
    { r: [46, 44, 28, 30, 8] } ] },
  { key: "BARK_TYLNY", view: "back", shapes: [
    { e: [36, 53, 7, 9] }, { e: [84, 53, 7, 9] } ] },
  { key: "ROMBOIDALNE", view: "back", shapes: [
    { r: [51, 62, 18, 18, 4] } ] },
  { key: "NAJSZERSZY_GRZBIETU", view: "back", shapes: [
    { r: [41, 78, 16, 36, 6] }, { r: [63, 78, 16, 36, 6] } ] },
  { key: "PROSTOWNIKI_GRZBIETU", view: "back", shapes: [
    { r: [55, 84, 10, 40, 4] } ] },
  { key: "TRICEPS", view: "back", shapes: [
    { r: [31, 70, 9, 25, 4] }, { r: [80, 70, 9, 25, 4] } ] },
  { key: "PRZEDRAMIE", view: "back", shapes: [
    { r: [29, 98, 9, 27, 4] }, { r: [82, 98, 9, 27, 4] } ] },
  { key: "POSLADKI", view: "back", shapes: [
    { r: [44, 126, 14, 28, 7] }, { r: [62, 126, 14, 28, 7] } ] },
  { key: "ODWODZICIELE", view: "back", shapes: [
    { r: [44, 130, 6, 36, 3] }, { r: [70, 130, 6, 36, 3] } ] },
  { key: "DWUGLOWY_UDA", view: "back", shapes: [
    { r: [45, 158, 12, 50, 6] }, { r: [63, 158, 12, 50, 6] } ] },
  { key: "PRZYWODZICIELE", view: "back", shapes: [
    { r: [54, 160, 4, 42, 2] }, { r: [62, 160, 4, 42, 2] } ] },
  { key: "LYDKA", view: "back", shapes: [
    { r: [46, 224, 10, 44, 5] }, { r: [64, 224, 10, 44, 5] } ] },
];

/** Kontur sylwetki — wspólny dla obu widoków (szkic, nie anatomia).
 *  Osobne kształty głowy, tułowia, ramion i nóg: dzięki temu podświetlona
 *  partia zawsze leży wewnątrz właściwej części ciała. */
const SILHOUETTE = [
  "M60 5c-7.5 0-13.5 6.5-13.5 14.5S52.5 35 60 35s13.5-6.5 13.5-15.5S67.5 5 60 5z",
  "M54 33h12v9H54z",
  "M36 42h48l-7 60 3 40H40l3-40z",
  "M35 43l10 3-5 88-13-2z",
  "M85 43l-10 3 5 88 13-2z",
  "M43 141h15l-2 68 1 80H45l-1-80z",
  "M62 141h15l-1 68 1 80H63l1-80z",
  "M43 289h15v6H43zM62 289h15v6H62z",
].join(" ");

function shapeEl(shape: Shape, index: number, className: string) {
  if ("r" in shape) {
    const [x, y, w, h, radius] = shape.r;
    return <rect key={index} x={x} y={y} width={w} height={h}
      rx={radius ?? 4} className={className} />;
  }
  const [cx, cy, rx, ry] = shape.e;
  return <ellipse key={index} cx={cx} cy={cy} rx={rx} ry={ry} className={className} />;
}

function Figure({ view, title, primary, secondary, height }: {
  view: "front" | "back";
  title: string;
  primary: Set<string>;
  secondary: Set<string>;
  height: number;
}) {
  const regions = REGIONS.filter((r) => r.view === view);
  return (
    <figure className="mmap__fig">
      {/* Sam rysunek jest dekoracją treści opisanej słowami obok — opis
          dostępny niesie podpis, a listy mięśni są w sekcji tekstowej. */}
      <svg viewBox="0 0 120 300" height={height} className="mmap__svg" aria-hidden>
        <path d={SILHOUETTE} className="mmap__body" />
        {regions.map((region) => {
          const state = primary.has(region.key)
            ? "mmap__region mmap__region--primary"
            : secondary.has(region.key)
              ? "mmap__region mmap__region--secondary"
              : "mmap__region";
          return (
            <g key={`${region.key}-${view}`}>
              {region.shapes.map((s, i) => shapeEl(s, i, state))}
            </g>
          );
        })}
      </svg>
      <figcaption className="mmap__cap">{title}</figcaption>
    </figure>
  );
}

/** Szkic sylwetki z podświetlonymi partiami: mocniej główne, słabiej
 *  pomocnicze. Klucze pochodzą ze wspólnego słownika MUSCLE_LABELS
 *  (kontrakt z backendem — `dzik_os/muscles.py`); klucz spoza słownika jest
 *  po prostu pomijany, żeby rysunek nigdy nie wywrócił karty ćwiczenia. */
export function MuscleMap({ primary, secondary, height = 190 }: {
  primary: string[];
  secondary?: string[];
  height?: number;
}) {
  const known = (keys: string[]) => keys.filter((k) => k in MUSCLE_LABELS);
  const primarySet = new Set(known(primary));
  const secondarySet = new Set(known(secondary ?? []).filter((k) => !primarySet.has(k)));
  if (primarySet.size === 0 && secondarySet.size === 0) return null;
  return (
    <div className="mmap">
      <div className="mmap__figs">
        <Figure view="front" title="Przód" height={height}
          primary={primarySet} secondary={secondarySet} />
        <Figure view="back" title="Tył" height={height}
          primary={primarySet} secondary={secondarySet} />
      </div>
      <p className="mmap__legend">
        <span className="mmap__key mmap__key--primary" aria-hidden /> główne
        {secondarySet.size > 0 && (
          <>
            {" "}<span className="mmap__key mmap__key--secondary" aria-hidden /> pomocnicze
          </>
        )}
      </p>
      <p className="mmap__note dim">
        Szkic orientacyjny — pokazuje okolicę ciała, która pracuje, a nie
        dokładny przebieg mięśni.
      </p>
    </div>
  );
}
