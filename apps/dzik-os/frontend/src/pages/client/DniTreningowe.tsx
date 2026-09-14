/**
 * Karta „Twoje dni treningowe” (0.71.0) — nakładka klienta na dni tygodnia
 * planu trenera. Wersje planu pozostają nietknięte: klient wybiera dzień
 * tygodnia dla każdej jednostki (prefill z propozycji trenera), zapisuje
 * albo wraca do propozycji. Zero rekomendacji — system nie proponuje „lepszych”
 * dni. Tryb „trener” = tylko odczyt (dzień wg klienta przy jednostce).
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../../api";
import { WEEKDAYS } from "../../dates";
import { Icon } from "../../components";
import { DniPlanu } from "../../types";

/** Etykieta odznaki przy jednostce: „pon. (Twój wybór)” / „pon. (propozycja trenera)”. */
export function etykietaDnia(source: DniPlanu["source"], weekday: number | null, tryb: "klient" | "trener" = "klient"): string | null {
  if (weekday == null) return source === "client" ? (tryb === "klient" ? "— (Twój wybór)" : "— (wg klienta)") : null;
  const dzien = WEEKDAYS[weekday - 1];
  if (source === "client") return tryb === "klient" ? `${dzien} (Twój wybór)` : `${dzien} (wg klienta)`;
  return `${dzien} (propozycja trenera)`;
}

/** Błąd zapisu: pole przypisujemy do jednostki tylko, gdy `errors[0].field`
 * jest jej kluczem; inne pola (np. `choices.0.weekday` z walidacji schematu)
 * dostają ogólny komunikat, żeby nic nie znikało bez słowa. */
function poleZBledu(e: unknown, klucze: string[]): { msg: string; field: string | null } {
  const err = e as ApiError;
  const body = (err?.body ?? {}) as { errors?: { field?: string }[] };
  const field = body.errors?.[0]?.field;
  return { msg: err?.message ?? "Nie udało się zapisać dni.", field: field && klucze.includes(field) ? field : null };
}

export default function DniTreningowe({ clientId, planId, tryb, onZmiana }: {
  clientId: string;
  planId: string;
  tryb: "klient" | "trener";
  /** Po każdym odczycie/zapisie — rodzic dostaje aktualny układ (odznaki przy dniach). */
  onZmiana?: (dane: DniPlanu) => void;
}) {
  const [dane, setDane] = useState<DniPlanu | null>(null);
  const [form, setForm] = useState<Record<string, number | null>>({});
  const [busy, setBusy] = useState(false);
  const [blad, setBlad] = useState<{ msg: string; field: string | null } | null>(null);
  const [sukces, setSukces] = useState<string | null>(null);
  const [bladOdczytu, setBladOdczytu] = useState<string | null>(null);

  const przyjmij = useCallback((d: DniPlanu) => {
    setDane(d);
    setForm(Object.fromEntries(d.days.map((x) => [x.day_key, x.weekday])));
    onZmiana?.(d);
  }, [onZmiana]);

  const zaladuj = useCallback(() => {
    setBladOdczytu(null);
    api.get<DniPlanu>(`/api/clients/${clientId}/plans/${planId}/dni`)
      .then(przyjmij)
      .catch((e) => setBladOdczytu((e as Error).message));
  }, [clientId, planId, przyjmij]);
  useEffect(zaladuj, [zaladuj]);

  async function wykonaj(fn: () => Promise<DniPlanu>, komunikat: string) {
    setBusy(true); setBlad(null); setSukces(null);
    try {
      przyjmij(await fn());
      setSukces(komunikat);
    } catch (e) {
      setBlad(poleZBledu(e, (dane?.days ?? []).map((x) => x.day_key)));
    } finally {
      setBusy(false);
    }
  }

  const zapisz = () => wykonaj(
    () => api.put<DniPlanu>(`/api/clients/${clientId}/plans/${planId}/dni`, {
      choices: Object.entries(form).map(([day_key, weekday]) => ({ day_key, weekday })),
    }),
    "Zapisano dni. Trening z dzisiejszego dnia zobaczysz na ekranie „Dzisiaj”.",
  );
  const wrocDoTrenera = () => wykonaj(
    () => api.del<DniPlanu>(`/api/clients/${clientId}/plans/${planId}/dni`),
    "Wrócono do propozycji trenera.",
  );

  if (bladOdczytu) {
    // Trener: brak dostępu (np. cofnięta zgoda) = brak linii, nie komunikat o awarii.
    if (tryb === "trener") return null;
    return (
      <div className="card" data-testid="dni-treningowe">
        <p className="dim" style={{ margin: 0 }}>Nie udało się wczytać dni treningowych. {bladOdczytu}{" "}
          <button type="button" className="btn btn--ghost btn--small" onClick={zaladuj}>Spróbuj ponownie</button></p>
      </div>
    );
  }
  if (!dane || dane.days.length === 0) return null;

  const zmieniony = dane.days.some((x) => (form[x.day_key] ?? null) !== x.weekday);
  const nieaktualne = dane.stale_keys.length > 0;

  if (tryb === "trener") {
    if (dane.source !== "client") return null;
    return (
      <p className="dim" style={{ fontSize: "0.85rem", margin: "6px 0" }} data-testid="dni-treningowe-trener">
        <Icon name="calendar" size={14} /> Klient wybrał dni tygodnia:{" "}
        {dane.days.map((x) => `${x.name} — ${x.weekday ? WEEKDAYS[x.weekday - 1] : "—"}`).join(", ")}.
        {nieaktualne && " Część wpisów dotyczy jednostek z poprzedniej wersji."}
      </p>
    );
  }

  return (
    <div className="card" data-testid="dni-treningowe">
      <h2><Icon name="calendar" /> Twoje dni treningowe</h2>
      <p className="dim" style={{ margin: "4px 0 8px", fontSize: "0.85rem" }}>
        {dane.source === "client"
          ? "Obowiązuje Twój układ. Jednostka bez dnia to dzień wolny od niej."
          : "Wybierz, w które dni tygodnia robisz poszczególne jednostki. Na start podpowiadamy propozycję trenera — możesz ją zmienić."}
      </p>
      {nieaktualne && (
        <p className="alert alert--info" role="status" data-testid="dni-nieaktualne">
          Plan się zmienił — sprawdź dni tygodnia i zapisz je ponownie.
        </p>
      )}
      {dane.days.map((x) => {
        const id = `dni-${x.day_index}`;
        const bladPola = blad?.field === x.day_key;
        return (
          <div key={x.day_key} style={{ marginBottom: 6 }}>
            <label htmlFor={id} style={{ margin: "6px 0 3px" }}>{x.name}</label>
            <select id={id} value={form[x.day_key] ?? ""} disabled={busy}
              aria-invalid={bladPola || undefined}
              aria-describedby={bladPola ? `${id}-blad` : undefined}
              onChange={(e) => { setSukces(null); setBlad(null);
                setForm({ ...form, [x.day_key]: e.target.value ? Number(e.target.value) : null }); }}>
              <option value="">— (bez dnia)</option>
              {WEEKDAYS.map((w, i) => <option key={i} value={i + 1}>{w}</option>)}
            </select>
            {bladPola && <p id={`${id}-blad`} className="alert alert--warn" role="alert" style={{ margin: "4px 0 0" }}>{blad?.msg}</p>}
          </div>
        );
      })}
      {blad && !blad.field && <p className="alert alert--warn" role="alert">{blad.msg}</p>}
      {sukces && <p className="alert alert--info" role="status">{sukces}</p>}
      <div className="row" style={{ marginTop: 8 }}>
        <button type="button" className="btn btn--small" onClick={zapisz} disabled={busy || (!zmieniony && dane.source === "client")}>
          {busy ? "Zapisywanie…" : "Zapisz dni"}
        </button>
        {dane.source === "client" && (
          <button type="button" className="btn btn--ghost btn--small" onClick={wrocDoTrenera} disabled={busy}>
            Wróć do propozycji trenera
          </button>
        )}
        {dane.source === "client" && <Link to="/" className="dim" style={{ fontSize: "0.85rem" }}>Zobacz „Dzisiaj” →</Link>}
      </div>
    </div>
  );
}
