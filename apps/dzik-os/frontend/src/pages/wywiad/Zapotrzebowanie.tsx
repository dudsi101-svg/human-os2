/**
 * Karta „Bilans kaloryczny” — wspólna dla aplikacji klienta (zakładki Wywiad
 * i Dieta) i panelu trenera (Wywiad, Dieta). Źródło: GET
 * /api/clients/{id}/zapotrzebowanie.
 *
 * Dwa widoki ze specyfikacji właściciela: klienta (§6.1 — cztery liczby,
 * każda z jednym zdaniem „skąd to”) i trenera (§6.2 — oba PPM z różnicą,
 * rozbicie CPM na składniki z podstawieniem, flagi, historia, nadpisanie).
 * Wszystkie filtry są po stronie serwera: przy status="hidden" klient
 * dostaje sam komunikat, a flagi z ekranu zdrowotnego nie wychodzą do
 * trenera bez zgody. 404 = moduł wyłączony → karta się nie renderuje.
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api";
import { plDateTime } from "../../dates";
import { ErrorBox } from "../../components";
import { ZapotrzebowanieOut, ZapotrzebowanieSzacunek } from "../../types";

export function useZapotrzebowanie(clientId: string) {
  const [dane, setDane] = useState<ZapotrzebowanieOut | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const zaladuj = useCallback(() => {
    setError(null);
    api.get<ZapotrzebowanieOut>(`/api/clients/${clientId}/zapotrzebowanie`).then(setDane).catch((e) => {
      if (e instanceof ApiError && e.status === 404) { setDane(null); return; }
      setError((e as Error).message);
    });
  }, [clientId]);
  useEffect(zaladuj, [zaladuj]);
  return { dane, error, zaladuj };
}

/** „1,44” zamiast „1.44”; bez zer końcowych. */
function pl(x: number | null | undefined, miejsc = 2): string {
  if (x === null || x === undefined) return "—";
  return x.toFixed(miejsc).replace(/\.?0+$/, "").replace(".", ",") || "0";
}

function kcal(x: number | null | undefined): string {
  return x === null || x === undefined ? "—" : `${x} kcal`;
}

/** Cztery liczby ze specyfikacji §6.1 — każda z jednym zdaniem wyjaśnienia. */
function Liczby({ e, tryb }: { e: ZapotrzebowanieSzacunek; tryb: "klient" | "trener" }) {
  const cel = e.override ? e.override.kcal : (e.target_kcal ?? e.kcal);
  const t = e.tempo;
  const zakresTempa = t && t.kg_tydzien_od !== null && t.kg_tydzien_do !== null
    ? `~${pl(t.kg_tydzien_od, 1)}–${pl(t.kg_tydzien_do, 1)} kg tygodniowo ${t.kg_tydzien > 0 ? "w dół" : "w górę"}`
    : "bez zmiany masy";
  return (
    <div className="stat-grid bilans__liczby">
      <div className="stat">
        <b>{kcal(e.ppm_used ?? e.ppm)}</b>
        <span>Spoczynek (PPM) — tyle spala Twoje ciało, gdybyś cały dzień leżał</span>
      </div>
      <div className="stat">
        <b data-testid="bilans-cpm">{kcal(e.cpm)}</b>
        <span>
          Cały dzień (CPM){e.cpm_min && e.cpm_max ? ` · zakres ${e.cpm_min}–${e.cpm_max}` : ""}
          {" "}— z Twoją aktywnością i treningami
        </span>
      </div>
      <div className="stat">
        <b data-testid="zapotrzebowanie-kcal">≈ {cel} kcal / dzień</b>
        <span>
          {e.override
            ? "Twój cel — ustalenie trenera"
            : `Twój cel — ${e.korekta_pct === 0 ? "bez korekty" : `korekta ${e.korekta_pct > 0 ? "+" : "−"}${Math.abs(e.korekta_pct)} %`}`}
        </span>
      </div>
      {e.macro && (
        <div className="stat">
          <b data-testid="bilans-makro">B {e.macro.bialko_g} g · T {e.macro.tluszcz_g} g · W {e.macro.wegle_g} g</b>
          <span>
            Makro na start ({e.macro.bialko_pct} / {e.macro.tluszcz_pct} / {e.macro.wegle_pct} %)
            {tryb === "trener" ? ` · białko liczone z ${pl(e.macro.bialko_z_masy_kg, 1)} kg` : ""}
          </span>
        </div>
      )}
      {t && (
        <div className="stat">
          <b>{zakresTempa}</b>
          <span>
            Oczekiwane tempo
            {t.tygodni_do_celu ? ` · do masy docelowej około ${t.tygodni_do_celu} tyg. (w praktyce dłużej — tempo zwalnia)` : ""}
          </span>
        </div>
      )}
      {t && t.przyrost_mies_od !== null && t.przyrost_mies_do !== null && (
        <div className="stat">
          <b>{pl(t.przyrost_mies_od, 2)}–{pl(t.przyrost_mies_do, 2)} kg / miesiąc</b>
          <span>Realistyczny przyrost mięśni przy Twoim stażu — reszta przyrostu masy to woda i tłuszcz</span>
        </div>
      )}
    </div>
  );
}

/** Rozbicie CPM na składniki z podstawieniem liczb (specyfikacja §6.2). */
function RozbicieCPM({ e }: { e: ZapotrzebowanieSzacunek }) {
  const ppm = e.ppm_used ?? e.ppm;
  const neat = e.neat_multiplier ?? null;
  const poNeat = neat ? Math.round(ppm * neat) : null;
  const roznicaPPM = e.ppm_mifflin && e.ppm_katch
    ? Math.round((100 * Math.abs(e.ppm_katch - e.ppm_mifflin)) / e.ppm_mifflin) : null;
  return (
    <div className="bilans__rozbicie">
      <h3 className="bilans__naglowek">Skąd wychodzi CPM</h3>
      <ul className="bilans__skladniki">
        <li>
          <span>PPM × aktywność poza treningiem</span>
          <b>{ppm} × {pl(neat)} = {poNeat !== null ? `${poNeat} kcal` : "—"}</b>
        </li>
        <li>
          <span>Trening (na dzień, uśredniony z tygodnia)</span>
          <b>+ {kcal(e.training_kcal_day)}</b>
        </li>
        <li>
          <span>Termiczny efekt pożywienia (10 %)</span>
          <b>+ {kcal(e.tef)}</b>
        </li>
        <li className="bilans__skladniki-suma">
          <span>CPM (zakres ±7 %)</span>
          <b>{e.cpm} kcal · {e.cpm_min}–{e.cpm_max}</b>
        </li>
      </ul>
      {e.ppm_mifflin && e.ppm_katch && (
        <p className="dim bilans__ppm">
          PPM Mifflin-St Jeor {e.ppm_mifflin} kcal · Katch-McArdle {e.ppm_katch} kcal
          {roznicaPPM !== null ? ` (różnica ${roznicaPPM} %)` : ""} — użyty{" "}
          {e.ppm_source === "katch_mcardle" ? "Katch-McArdle" : "Mifflin-St Jeor"}.
        </p>
      )}
      {e.bmi != null && <p className="dim bilans__ppm">BMI {pl(e.bmi, 1)}</p>}
    </div>
  );
}

function Flagi({ e }: { e: ZapotrzebowanieSzacunek }) {
  if (!e.flags.length) return null;
  return (
    <div role="group" aria-label="Flagi i ograniczenia">
      {e.flags.map((f) => (
        <p key={f.code} className={f.poziom === "warn" ? "alert alert--warn" : "alert alert--info"}>
          <b>{f.etykieta}.</b> {f.opis}
        </p>
      ))}
    </div>
  );
}

export default function ZapotrzebowanieKarta({ clientId, tryb, linkDoWywiadu, onOtworz, kompakt = false }: {
  clientId: string;
  tryb: "klient" | "trener";
  /** Link do formularza (klient: /wywiad?typ=zapotrzebowanie). */
  linkDoWywiadu?: string;
  /** Trener: otwarcie formularza w trybie „wspólnie”. */
  onOtworz?: () => void;
  /** Zakładka Dieta: bez historii i rozbicia w nagłówku. */
  kompakt?: boolean;
}) {
  const { dane, error, zaladuj } = useZapotrzebowanie(clientId);
  const [pokazPodstawienie, setPokazPodstawienie] = useState(false);
  const [nadpisanie, setNadpisanie] = useState<{ kcal: string; reason: string } | null>(null);
  const [zapis, setZapis] = useState(false);
  const [blad, setBlad] = useState<string | null>(null);

  if (dane === null) return null; // moduł wyłączony
  if (error) return <div className="card"><ErrorBox error={error} onRetry={zaladuj} /></div>;
  if (dane === undefined) return null;
  if (!dane.access.ok) return null; // trener bez zgód — komunikat pokazuje zakładka Wywiad

  async function wyslijNadpisanie(nowe: number | null, reason: string) {
    setZapis(true); setBlad(null);
    try {
      await api.put(`/api/clients/${clientId}/zapotrzebowanie/nadpisanie`, { kcal: nowe, reason });
      setNadpisanie(null); zaladuj();
    } catch (e) { setBlad((e as Error).message); } finally { setZapis(false); }
  }
  async function odblokuj() {
    setZapis(true); setBlad(null);
    try { await api.post(`/api/clients/${clientId}/zapotrzebowanie/odblokuj`, {}); zaladuj(); }
    catch (e) { setBlad((e as Error).message); } finally { setZapis(false); }
  }

  const e = dane.estimate;
  // Nadpisanie dotyczy wersji: nowa wersja wywiadu liczy się ze wzoru, a poprzednie ustalenie wygasa.
  const wygasle = e && !e.override ? dane.history?.find((h) => h.version_no < e.version_no && h.override_kcal != null) : undefined;
  return (
    <div className="card" role="region" aria-label="Bilans kaloryczny" data-testid="zapotrzebowanie-karta">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}>Bilans kaloryczny</h2>
        {e && <span className="badge">wersja {e.version_no}</span>}
      </div>
      {dane.status === "none" && (
        <>
          <p className="dim" style={{ marginBottom: 6 }}>
            {tryb === "klient"
              ? "Pięć krótkich ekranów o ciele, ruchu, treningu i celu — wzory policzą Twój bilans kaloryczny, a trener go potwierdzi."
              : "Klient nie wypełnił jeszcze wywiadu zapotrzebowania. Możesz uzupełnić go wspólnie podczas konsultacji."}
          </p>
          {linkDoWywiadu && <Link className="btn btn--small" to={linkDoWywiadu}>Wypełnij wywiad</Link>}
          {onOtworz && <button type="button" className="btn btn--ghost btn--small" onClick={onOtworz}>Uzupełnij wspólnie</button>}
        </>
      )}
      {dane.status === "hidden" && (
        <>
          <p className="alert alert--info" role="status">{dane.message}</p>
          {dane.hidden_reason === "maloletni" && (
            <p className="dim">Wzory kaloryczne, z których korzystamy, są policzone dla osób dorosłych — dlatego wynik zostaje u trenera.</p>
          )}
        </>
      )}
      {dane.status === "ok" && e && (
        <>
          {dane.message && <p className="alert alert--info" role="status">{dane.message}</p>}
          {e.legacy ? (
            <p style={{ fontSize: "1.4rem", margin: "6px 0 2px" }}>
              <b data-testid="zapotrzebowanie-kcal">≈ {e.kcal_effective} kcal / dzień</b>
            </p>
          ) : (
            <Liczby e={e} tryb={tryb} />
          )}
          {e.override ? (
            <p className="dim" style={{ marginTop: 6 }}>
              Ustalone przez trenera ({plDateTime(e.override.at)}): {e.override.reason}. Wzór dawał {e.kcal} kcal.
            </p>
          ) : (
            tryb === "klient" && !e.legacy && (
              <p className="dim" style={{ marginTop: 6 }}>
                To punkt startowy, nie zalecenie. Po 2–3 tygodniach trener skoryguje kalorie na podstawie Twoich ważeń.
                Błąd takich wzorów to około ±10 % — dlatego CPM pokazujemy jako zakres.
              </p>
            )
          )}
          <Flagi e={e} />
          {e.ostrzezenia.map((o) => <p key={o} className="alert alert--warn">{o}</p>)}
          {tryb === "trener" && dane.coach_note && (
            <p className="alert alert--info" role="status">{dane.coach_note}</p>
          )}
          {tryb === "trener" && !kompakt && !e.legacy && <RozbicieCPM e={e} />}
          {tryb === "trener" && e.hidden_for_client && (
            <div className="alert alert--warn">
              {/* Powód ukrycia wynika z odpowiedzi zdrowotnej, więc bez zgody na
                  dane zdrowotne serwer go nie podaje i piszemy neutralnie
                  (przegląd PR #80, P0). Sam fakt ukrycia trener widzieć musi. */}
              <span role="status">{e.hidden_reason === "zaburzenia"
                ? "Na pytanie o zaburzenia odżywiania klient odpowiedział „Tak”, „Nie wiem” albo „Wolę omówić z trenerem” — liczby są przed nim ukryte do rozmowy."
                : e.hidden_reason === "maloletni"
                  ? "Klient jest niepełnoletni — liczby są przed nim ukryte do czasu rozmowy z opiekunem."
                  : "Klient nie widzi liczb do czasu rozmowy z Tobą."}</span>
              {" "}<button type="button" className="btn btn--small" disabled={zapis} onClick={() => void odblokuj()}>Odsłoń wynik klientowi</button>
            </div>
          )}
          {tryb === "trener" && wygasle && (
            <p className="alert alert--info" role="status">
              Poprzednie ustalenie (v{wygasle.version_no}: {wygasle.override_kcal} kcal) wygasło z nową wersją wywiadu — ustal ponownie, jeśli nadal obowiązuje.
            </p>
          )}
          <button type="button" className="btn btn--ghost btn--small" aria-expanded={pokazPodstawienie}
            onClick={() => setPokazPodstawienie((v) => !v)}>
            {pokazPodstawienie ? "Ukryj podstawienie" : "Skąd ta liczba?"}
          </button>
          {pokazPodstawienie && (
            <>
              <small className="dim" style={{ display: "block" }}>
                PPM — ile organizm spala w spoczynku; CPM — ile spalasz w ciągu całego dnia.
                {e.override ? " Podstawienie dotyczy wzoru, nie ustalenia trenera." : ""}
              </small>
              <ol className="bilans__podstawienie" aria-label="Podstawienie do wzoru">
                {e.podstawienie.map((w) => <li key={w}>{w}</li>)}
              </ol>
            </>
          )}
          {tryb === "trener" && (
            <div style={{ marginTop: 8 }}>
              {nadpisanie ? (
                <div className="field-row" style={{ alignItems: "end" }}>
                  <div><label htmlFor="zk-nadpisz-kcal">kcal / dzień (Twoja decyzja)</label>
                    <input id="zk-nadpisz-kcal" inputMode="numeric" value={nadpisanie.kcal} aria-describedby="zk-nadpisz-zakres"
                      onChange={(ev) => setNadpisanie({ ...nadpisanie, kcal: ev.target.value })} />
                    <small id="zk-nadpisz-zakres" className="dim">800–8000 kcal</small></div>
                  <div><label htmlFor="zk-nadpisz-powod">Powód (klient go zobaczy)</label>
                    <input id="zk-nadpisz-powod" value={nadpisanie.reason} maxLength={500}
                      onChange={(ev) => setNadpisanie({ ...nadpisanie, reason: ev.target.value })} /></div>
                  <div className="row" style={{ gap: 6 }}>
                    <button type="button" className="btn btn--small" disabled={zapis || !Number(nadpisanie.kcal) || !nadpisanie.reason.trim()}
                      onClick={() => void wyslijNadpisanie(Number(nadpisanie.kcal), nadpisanie.reason)}>Zapisz</button>
                    <button type="button" className="btn btn--ghost btn--small" onClick={() => setNadpisanie(null)}>Anuluj</button>
                  </div>
                </div>
              ) : (
                <div className="row" style={{ gap: 6 }}>
                  <button type="button" className="btn btn--ghost btn--small"
                    onClick={() => setNadpisanie({ kcal: String(e.kcal_effective), reason: e.override?.reason ?? "" })}>
                    {e.override ? "Zmień ustalenie" : "Nadpisz wynik"}
                  </button>
                  {e.override && (
                    <button type="button" className="btn btn--ghost btn--small" disabled={zapis}
                      onClick={() => void wyslijNadpisanie(null, "powrót do wzoru")}>
                      Wróć do wzoru
                    </button>
                  )}
                  {onOtworz && <button type="button" className="btn btn--ghost btn--small" onClick={onOtworz}>Zaktualizuj wywiad wspólnie</button>}
                </div>
              )}
              {blad && <p className="alert alert--error" role="alert">{blad}</p>}
              {!kompakt && dane.history && dane.history.length > 1 && (
                <div className="bilans__przewijanie" tabIndex={0} role="group"
                  aria-label="Historia wywiadów — tabela przewijana w poziomie">
                <table className="bilans__historia">
                  <caption className="dim">Historia wywiadów: masa i wynik w czasie</caption>
                  <thead>
                    <tr><th scope="col">Wersja</th><th scope="col">Masa</th><th scope="col">CPM</th>
                      <th scope="col">Obowiązuje</th><th scope="col">Data</th></tr>
                  </thead>
                  <tbody>
                    {dane.history.map((h) => (
                      <tr key={h.version_no}>
                        <th scope="row">v{h.version_no}{h.legacy ? " (stary wzór)" : ""}</th>
                        <td>{h.masa_kg != null ? `${pl(h.masa_kg, 1)} kg` : "—"}</td>
                        <td>{h.cpm} kcal</td>
                        <td>{h.kcal_effective} kcal{h.override_kcal != null ? " (trener)" : ""}</td>
                        <td>{plDateTime(h.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
