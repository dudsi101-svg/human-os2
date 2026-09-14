import { KeyboardEvent, useRef, useState } from "react";
import { updateNotificationSettings, zapiszMotywWSesji } from "../api";
import { MOTYWY, Motyw, NAZWY_MOTYWOW, odczytajMotyw, ustawMotyw } from "../theme";

/**
 * Sekcja „Wygląd” w „Więcej” (0.74.0) — wybór motywu aplikacji, ten sam blok
 * dla klienta i trenera (każdy wybiera dla siebie; to samo konto = ten sam
 * wiersz ustawień). Dwie karty-przyciski jako grupa radiowa: podgląd kolorów,
 * nazwa, opis. Klawiatura: strzałki przenoszą fokus (bez zapisu — wybór to
 * świadome kliknięcie / Enter / Spacja), Home/End na skraje.
 *
 * Zapis: najpierw urządzenie (theme.ts — natychmiast widać), potem konto
 * (PUT /api/notifications/settings { theme }). Gdy konto nie odpowie, wybór
 * i tak obowiązuje na tym urządzeniu — komunikat mówi o tym wprost.
 */
export default function Wyglad() {
  const [motyw, setMotyw] = useState<Motyw>(odczytajMotyw);
  const [status, setStatus] = useState<{ tekst: string; blad: boolean } | null>(null);
  const przyciski = useRef<(HTMLButtonElement | null)[]>([]);

  async function wybierz(m: Motyw) {
    if (m === motyw) return;
    ustawMotyw(m);
    setMotyw(m);
    setStatus(null);
    try {
      await updateNotificationSettings({ theme: m });
      zapiszMotywWSesji(m); // kopia w sesji = konto (rotacja tokenu nie cofnie wyboru)
      setStatus({ tekst: "Zapisano na koncie — obowiązuje po zalogowaniu na innym urządzeniu.", blad: false });
    } catch {
      setStatus({
        tekst: "Motyw zmieniony na tym urządzeniu; nie udało się zapisać na koncie — spróbuj później.",
        blad: true,
      });
    }
  }

  function klawisz(e: KeyboardEvent<HTMLDivElement>) {
    const idx = MOTYWY.indexOf(motyw);
    const focused = przyciski.current.findIndex((b) => b === document.activeElement);
    const od = focused >= 0 ? focused : idx;
    let cel = -1;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") cel = (od + 1) % MOTYWY.length;
    else if (e.key === "ArrowLeft" || e.key === "ArrowUp") cel = (od - 1 + MOTYWY.length) % MOTYWY.length;
    else if (e.key === "Home") cel = 0;
    else if (e.key === "End") cel = MOTYWY.length - 1;
    if (cel >= 0) {
      e.preventDefault();
      przyciski.current[cel]?.focus();
    }
  }

  return (
    <div className="card wyglad">
      <h2 id="wyglad-tytul">Wygląd</h2>
      <p className="dim" style={{ fontSize: "0.85rem", margin: "0 0 10px" }}>
        Motyw wybierasz sam — ciemny na siłownię albo jasny czerwono-biały.
        Wybór zapisuje się na tym urządzeniu i na Twoim koncie.
      </p>
      <div className="wyglad__karty" role="radiogroup" aria-labelledby="wyglad-tytul" onKeyDown={klawisz}>
        {MOTYWY.map((m, i) => {
          const aktywny = m === motyw;
          return (
            <button
              key={m}
              type="button"
              role="radio"
              aria-checked={aktywny}
              tabIndex={aktywny ? 0 : -1}
              className={`wyglad__karta${aktywny ? " wyglad__karta--aktywna" : ""}`}
              data-motyw={m}
              ref={(el) => { przyciski.current[i] = el; }}
              onClick={() => wybierz(m)}
            >
              <span className={`wyglad__probka wyglad__probka--${m}`} aria-hidden="true">
                <i className="wyglad__probka-tlo"><b /><u /></i>
              </span>
              <span className="wyglad__opis">
                <b>{NAZWY_MOTYWOW[m].nazwa}</b>
                <small>{NAZWY_MOTYWOW[m].opis}</small>
              </span>
            </button>
          );
        })}
      </div>
      {status && (
        <p className={status.blad ? "alert alert--warn" : "dim"} role="status" style={{ fontSize: "0.82rem", margin: "10px 0 0" }}>
          {status.tekst}
        </p>
      )}
    </div>
  );
}
