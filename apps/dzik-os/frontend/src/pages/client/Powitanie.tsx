import { KeyboardEvent, useEffect, useRef, useState } from "react";
import { hasFeature } from "../../api";

/**
 * Powitanie po pierwszym logowaniu (0.70.0) — dwuetapowy samouczek.
 *
 * Pomoc, nie bramka: niczego nie blokuje, każdy krok da się pominąć
 * (Esc = „Pomiń na razie”), a całość otworzysz ponownie z „Więcej → Pomoc /
 * Samouczek”. Okno nie zbiera żadnych danych — tylko opisuje funkcje, które
 * istnieją w aplikacji; zgody i wywiady wyłącznie WSKAZUJE (decyzja zapada
 * tam, gdzie dotąd: Profil → „Prywatność i zgody”, zakładka „Wywiad”).
 *
 * Dostępność: role="dialog" + aria-modal + aria-labelledby (nagłówek h2
 * bieżącego kroku), fokus zamknięty w oknie (Tab/Shift+Tab zawijają się),
 * fokus startowy na nagłówku, przyciski to zwykłe <button> z tekstem.
 */
export type PowitaniePowod = "pomin" | "zaczynamy";

export default function Powitanie({
  imie,
  onZamknij,
}: {
  imie: string | null | undefined;
  /** „pomin” = Esc / „Pomiń na razie”; „zaczynamy” = „Rozumiem, zaczynajmy”. */
  onZamknij: (powod: PowitaniePowod) => void;
}) {
  const [krok, setKrok] = useState<1 | 2>(1);
  const okno = useRef<HTMLDivElement>(null);
  const naglowek = useRef<HTMLHeadingElement>(null);
  const postepy = hasFeature("monitoring_tab");
  const kto = (imie ?? "").trim();

  // Fokus startowy na nagłówku kroku (czytnik ekranu od razu czyta tytuł);
  // przy zmianie kroku — na nowym nagłówku. Przewijanie strony pod oknem
  // zatrzymane na czas wyświetlania.
  useEffect(() => {
    naglowek.current?.focus();
  }, [krok]);
  useEffect(() => {
    const poprzedni = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = poprzedni;
    };
  }, []);

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      onZamknij("pomin");
      return;
    }
    if (e.key !== "Tab" || !okno.current) return;
    // Pułapka fokusu: Tab z ostatniego elementu wraca do pierwszego,
    // Shift+Tab z pierwszego idzie na ostatni. Nagłówek (tabIndex -1) nie
    // należy do pętli — jest tylko celem fokusu startowego.
    const elementy = Array.from(
      okno.current.querySelectorAll<HTMLElement>("button:not([disabled])"),
    );
    if (elementy.length === 0) return;
    const pierwszy = elementy[0];
    const ostatni = elementy[elementy.length - 1];
    const aktywny = document.activeElement;
    if (e.shiftKey && (aktywny === pierwszy || !elementy.includes(aktywny as HTMLElement))) {
      e.preventDefault();
      ostatni.focus();
    } else if (!e.shiftKey && aktywny === ostatni) {
      e.preventDefault();
      pierwszy.focus();
    }
  }

  const zakladki = `Dzisiaj, Plan, Dieta, ${postepy ? "Postępy" : "Raport"}`;

  return (
    <div className="powitanie-tlo" data-testid="powitanie-samouczek">
      <div
        className="card powitanie-okno"
        role="dialog"
        aria-modal="true"
        aria-labelledby="powitanie-tytul"
        ref={okno}
        onKeyDown={onKeyDown}
      >
        <small className="dim">Krok {krok} z 2</small>
        {krok === 1 ? (
          <>
            <h2 id="powitanie-tytul" ref={naglowek} tabIndex={-1}>
              {kto ? `Cześć, ${kto}! Dobrze Cię widzieć.` : "Cześć! Dobrze Cię widzieć."}
            </h2>
            <p>
              To Twoje miejsce współpracy z trenerem. Na dole ekranu masz
              zakładki: <b>{zakladki}</b> — a więcej pod <b>„Więcej”</b>.
            </p>
            <p>Żeby ruszyć pełną parą, zrób dwie rzeczy:</p>
            <ol>
              <li>
                <b>Zgody</b> (Więcej → Profil, zgody i moje dane → „Prywatność
                i zgody”) — sam(a) decydujesz, czym się dzielisz. Bez nich część
                funkcji jest wyłączona, a wszystko cofniesz w każdej chwili.
              </li>
              <li>
                <b>Wywiady</b> (Więcej → Wywiad) — rozmowa startowa i głęboki
                wywiad. Dzięki nim trener ułoży plan pod Ciebie, a nie
                „uniwersalny”. Każde pytanie możesz pominąć.
              </li>
            </ol>
            <button type="button" className="btn" onClick={() => setKrok(2)}>
              Dalej
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => onZamknij("pomin")}>
              Pomiń na razie
            </button>
          </>
        ) : (
          <>
            <h2 id="powitanie-tytul" ref={naglowek} tabIndex={-1}>
              Co jeszcze warto wiedzieć
            </h2>
            <ul>
              <li>
                <b>Dieta</b> — gdy trener przypisze Ci dietę z szablonu, składnik,
                który nie pasuje, wymienisz na policzony przez aplikację zamiennik
                (Dieta → „↔ wymień”).
              </li>
              <li>
                <b>{postepy ? "Postępy" : "Postępy (Więcej → Monitoring i postępy)"}</b>
                {" "}— zapisuj wagę, obwody i wyniki treningów; zobaczysz trendy.
              </li>
              <li>
                <b>Wiedza</b> (Więcej → Baza wiedzy) — każde ćwiczenie ma opis
                techniki.
              </li>
              <li>
                <b>Raport</b> {postepy ? "(Więcej → Raport tygodniowy)" : "(zakładka Raport)"}
                {" "}— do cotygodniowego raportu warto dołączyć zdjęcia sylwetki.
              </li>
              <li>
                <b>Nagranie do trenera</b> — masz problem z ruchem? Nagraj
                krótkie nagranie i wyślij trenerowi w wiadomości (Więcej →
                Wiadomości).
              </li>
            </ul>
            <button type="button" className="btn" onClick={() => onZamknij("zaczynamy")}>
              Rozumiem, zaczynajmy
            </button>
            <p className="dim" style={{ fontSize: "0.8rem", margin: "10px 0 0" }}>
              Ten samouczek otworzysz ponownie w „Więcej” → Pomoc / Samouczek.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
