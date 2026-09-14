import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api, ApiError } from "./api";
import { Icon, Spinner } from "./components";
import { adresApiOpisu, adresKartyCwiczenia, kluczOpisu, RolaOpisu } from "./nazwy";
import { ExerciseLibraryItem, muscleLabels } from "./types";

/**
 * Opis ćwiczenia przy pozycji planu (0.75.0) — dla klienta (Plan, Dzisiaj,
 * pozycje bloków) i trenera (podgląd planu klienta).
 *
 * Po kliknięciu pobiera kartę z bazy trenera: po `exercise_id`, gdy pozycja
 * go ma; inaczej po znormalizowanej nazwie (serwer dopasowuje
 * deterministycznie, bez zgadywania). Rozwinięcie w miejscu to SKRÓT —
 * technika w punktach, najczęstsze błędy, pracujące mięśnie — a pełna karta
 * (warianty, tempo, bezpieczeństwo, wideo, mapa mięśni) jest jedno kliknięcie
 * dalej w Wiedzy, z powrotem tam, skąd klient przyszedł.
 *
 * Brak dopasowania jest uczciwym komunikatem, nie pustym przyciskiem —
 * a wynik (także brak) trafia do pamięci podręcznej na czas życia karty
 * przeglądarki, więc to samo ćwiczenie w kilku dniach to jedno żądanie.
 */

type Wpis =
  | { stan: "jest"; item: ExerciseLibraryItem }
  | { stan: "brak" }
  | { stan: "blad"; komunikat: string };

const cache = new Map<string, Wpis>();
const wToku = new Map<string, Promise<Wpis>>();

/** Do testów widoku: czyści pamięć podręczną (nie używane w aplikacji). */
export function wyczyscCacheOpisow(): void {
  cache.clear();
  wToku.clear();
}

async function pobierz(rola: RolaOpisu, exerciseId: string | null | undefined, nazwa: string): Promise<Wpis> {
  const klucz = `${rola}:${kluczOpisu(exerciseId, nazwa)}`;
  const gotowe = cache.get(klucz);
  if (gotowe) return gotowe;
  const trwa = wToku.get(klucz);
  if (trwa) return trwa;
  const p = api.get<ExerciseLibraryItem>(adresApiOpisu(rola, exerciseId, nazwa))
    .then<Wpis>((item) => ({ stan: "jest", item }))
    .catch<Wpis>((e) => {
      const err = e as ApiError;
      // 404 = brak dopasowania albo ćwiczenie zarchiwizowane: to ODPOWIEDŹ,
      // nie awaria — zapamiętujemy, żeby nie pytać w kółko.
      if (err.status === 404 || err.status === 422) return { stan: "brak" };
      return { stan: "blad", komunikat: err.message };
    })
    .then((w) => {
      if (w.stan !== "blad") cache.set(klucz, w);
      wToku.delete(klucz);
      return w;
    });
  wToku.set(klucz, p);
  return p;
}

const MAX_PUNKTOW = 6;

export function OpisCwiczenia({ exerciseId, name, rola = "klient", powrot, testid }: {
  exerciseId?: string | null;
  name: string;
  rola?: RolaOpisu;
  /** Dokąd wraca przycisk na karcie w Wiedzy (tylko ścieżka aplikacji). */
  powrot?: string | null;
  testid?: string;
}) {
  const [open, setOpen] = useState(false);
  const [wpis, setWpis] = useState<Wpis | null>(null);
  const [loading, setLoading] = useState(false);
  const loc = useLocation();
  // Bez jawnego `powrot` karta wraca dokładnie tam, gdzie klient/trener jest teraz.
  const wroc = powrot === undefined ? `${loc.pathname}${loc.search}` : powrot;
  const nazwa = name.trim();
  if (!nazwa && !exerciseId) return null;

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next && (wpis === null || wpis.stan === "blad") && !loading) {
      setLoading(true);
      pobierz(rola, exerciseId, nazwa).then(setWpis).finally(() => setLoading(false));
    }
  }

  const item = wpis?.stan === "jest" ? wpis.item : null;
  const kroki = item ? (item.steps.length > 0 ? item.steps : [item.how_to]).filter(Boolean) : [];
  return (
    <div style={{ marginTop: 6 }} data-testid={testid}>
      <button type="button" className="btn btn--ghost btn--small" aria-expanded={open}
        aria-label={`${open ? "Ukryj opis" : "Opis ćwiczenia"}: ${nazwa}`} onClick={toggle}>
        <Icon name={open ? "chevron-up" : "chevron-down"} size={16} />{" "}
        {open ? "Ukryj opis" : "Opis ćwiczenia"}
      </button>
      {open && (
        <div className="card" style={{ marginTop: 6 }} data-testid={testid ? `${testid}-tresc` : undefined}>
          {loading && <Spinner />}
          {wpis?.stan === "brak" && (
            <p className="dim" style={{ margin: 0 }}>
              {exerciseId
                ? "To ćwiczenie nie jest już dostępne w bazie trenera. Twój plan pozostaje bez zmian — zapytaj trenera, jeśli potrzebujesz opisu."
                : rola === "trener"
                  ? "Brak opisu tego ćwiczenia w Twojej bazie — dodaj je w Wiedzy → Ćwiczenia pod tą samą nazwą, a link pojawi się sam."
                  : "Brak opisu tego ćwiczenia w Wiedzy — trener nie opisał go jeszcze w swojej bazie. Zapytaj trenera, jeśli potrzebujesz techniki."}
            </p>
          )}
          {wpis?.stan === "blad" && (
            <p className="dim" style={{ margin: 0 }} role="alert">
              Nie udało się pobrać opisu ({wpis.komunikat}).{" "}
              <button type="button" className="btn btn--ghost btn--small" onClick={() => { setOpen(false); toggle(); }}>Spróbuj ponownie</button>
            </p>
          )}
          {item && (
            <>
              <b>{item.name}</b>
              {kroki.length > 0 && (
                <>
                  <h3 className="exercise-detail__h">Technika w punktach</h3>
                  <ol className="exercise-detail__list">
                    {kroki.slice(0, MAX_PUNKTOW).map((s, i) => <li key={i}>{s}</li>)}
                  </ol>
                  {kroki.length > MAX_PUNKTOW && <p className="dim" style={{ margin: 0, fontSize: "0.85rem" }}>… i {kroki.length - MAX_PUNKTOW} kolejnych w pełnym opisie.</p>}
                </>
              )}
              {item.mistakes.length > 0 && (
                <>
                  <h3 className="exercise-detail__h">Najczęstsze błędy</h3>
                  <ul className="exercise-detail__list">
                    {item.mistakes.slice(0, MAX_PUNKTOW).map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </>
              )}
              {(item.muscles_primary.length > 0 || item.muscles_secondary.length > 0) && (
                <p style={{ margin: "6px 0 0", fontSize: "0.9rem" }}>
                  <b>Mięśnie:</b> {muscleLabels(item.muscles_primary)}
                  {item.muscles_secondary.length > 0 && <span className="dim"> · pomocniczo {muscleLabels(item.muscles_secondary)}</span>}
                </p>
              )}
              <p style={{ margin: "8px 0 0" }}>
                <Link to={adresKartyCwiczenia(rola, item.id, wroc)} className="btn btn--small"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <Icon name="knowledge" size={16} /> Pełny opis w Wiedzy
                </Link>
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

/** Link do własnej karty ćwiczenia w Wiedzy przy pozycji edytora/szkicu
 * trenera (tylko gdy pozycja ma `exercise_id`; edytor ma zostać lekki —
 * bez rozwijania treści). Powrót prowadzi na bieżący ekran. */
export function LinkKartyTrenera({ exerciseId }: { exerciseId: string | null | undefined }) {
  const loc = useLocation();
  if (!exerciseId) return null;
  return (
    <Link to={adresKartyCwiczenia("trener", exerciseId, `${loc.pathname}${loc.search}`)}
      style={{ marginLeft: 8, fontSize: "0.85rem" }}>
      Karta w Wiedzy
    </Link>
  );
}
