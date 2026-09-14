/**
 * Panel „Nawyki” (0.63.0) — wspólny dla ekranu „Dzisiaj” klienta i karty
 * klienta u trenera (zakładka Harmonogram). Trzy nawyki z codziennym,
 * cofalnym odhaczaniem, delikatnym postępem i absolutorium. Zero streaków,
 * zero czerwieni, zero komunikatów-kar — postęp opisuje serwer
 * (`progress_label`), a łagodny decay jest niewidoczny jako „kara”.
 */
import { useCallback, useEffect, useState } from "react";
import { api } from "../../api";
import { Icon } from "../../components";
import { HabitOut } from "../../types";

const DNI = [[1, "pn"], [2, "wt"], [3, "śr"], [4, "cz"], [5, "pt"], [6, "so"], [7, "nd"]] as const;

function dniTekst(days: string): string {
  const set = new Set(days.split(",").map((x) => x.trim()));
  if (set.size >= 7) return "codziennie";
  return DNI.filter(([n]) => set.has(String(n))).map(([, l]) => l).join(", ");
}

type Form = { name: string; days: number[]; target_days: string; author_note: string };
const PUSTY: Form = { name: "", days: [1, 2, 3, 4, 5, 6, 7], target_days: "66", author_note: "" };

export default function PanelNawykow({ clientId, tryb, habits: zewn, onZmiana }: {
  clientId: string;
  tryb: "klient" | "trener";
  /** „Dzisiaj” podaje nawyki z agregatu; bez tej właściwości panel ładuje je sam. */
  habits?: HabitOut[];
  /** Po każdej zmianie (odhaczenie, dodanie…) — rodzic odświeża swoje dane. */
  onZmiana?: () => void;
}) {
  const [wlasne, setWlasne] = useState<HabitOut[] | null>(null);
  const [zarzadzanie, setZarzadzanie] = useState(false);
  const [form, setForm] = useState<Form | null>(null);
  const [edycja, setEdycja] = useState<{ id: string; name: string; target_days: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [blad, setBlad] = useState<string | null>(null);

  const zaladuj = useCallback(() => {
    if (zewn) { onZmiana?.(); return; }
    api.get<{ habits: HabitOut[] }>(`/api/clients/${clientId}/habits`).then((d) => setWlasne(d.habits))
      .catch((e) => setBlad((e as Error).message));
  }, [clientId, zewn, onZmiana]);
  useEffect(() => { if (!zewn) zaladuj(); }, [zewn, zaladuj]);

  const nawyki = zewn ?? wlasne ?? [];
  const aktywne = nawyki.filter((h) => h.status === "ACTIVE");
  const absolutoria = nawyki.filter((h) => h.status === "GRADUATED");
  const wolne = Math.max(0, 3 - aktywne.length);

  async function wykonaj(id: string, fn: () => Promise<unknown>) {
    setBusy(id); setBlad(null);
    try { await fn(); zaladuj(); } catch (e) { setBlad((e as Error).message); } finally { setBusy(null); }
  }
  const odhacz = (h: HabitOut) => wykonaj(h.id, () =>
    api.post(`/api/clients/${clientId}/habits/${h.id}/complete`, { done: !h.done_today }));
  const archiwizuj = (h: HabitOut) => wykonaj(h.id, () =>
    api.patch(`/api/clients/${clientId}/habits/${h.id}`, { status: "ARCHIVED" }));
  const zostaw = (h: HabitOut) => wykonaj(h.id, () =>
    api.patch(`/api/clients/${clientId}/habits/${h.id}`, { ack: true }));
  const wymien = async (h: HabitOut) => { await archiwizuj(h); setZarzadzanie(true); setForm({ ...PUSTY }); };

  async function dodaj(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    await wykonaj("form", () => api.post(`/api/clients/${clientId}/habits`, {
      name: form.name.trim(), days_of_week: (form.days.length ? [...form.days].sort() : [1, 2, 3, 4, 5, 6, 7]).join(","),
      target_days: Number(form.target_days) || 66, author_note: form.author_note.trim() || null,
    }));
    setForm(null);
  }
  async function zapiszEdycje(e: React.FormEvent) {
    e.preventDefault();
    if (!edycja) return;
    await wykonaj(edycja.id, () => api.patch(`/api/clients/${clientId}/habits/${edycja.id}`, {
      name: edycja.name.trim(), target_days: Number(edycja.target_days) || undefined,
    }));
    setEdycja(null);
  }

  const pusty = nawyki.length === 0;
  return (
    <div className="card" data-testid="panel-nawykow">
      <div className="row row--between">
        <h2 style={{ margin: 0 }}><Icon name="target" /> Nawyki</h2>
        <button type="button" className="btn btn--ghost btn--small" aria-expanded={zarzadzanie}
          onClick={() => { setZarzadzanie((v) => !v); setForm(null); setEdycja(null); }}>
          {zarzadzanie ? "Gotowe" : pusty ? "Dodaj nawyk" : "Zarządzaj"}
        </button>
      </div>
      {pusty && !zarzadzanie && (
        <p className="dim" style={{ marginBottom: 0 }}>
          {tryb === "klient"
            ? "Wybierz do trzech małych czynności, które chcesz utrwalić. Odhaczasz je codziennie, a gdy się utrwalą — aplikacja przestaje o nie pytać."
            : "Klient nie ma jeszcze nawyków. Możesz zaproponować do trzech startowych — klient może je zmienić."}
        </p>
      )}
      {blad && <p className="alert alert--error" role="alert">{blad}</p>}

      {aktywne.map((h) => (
        <div className="exercise" key={h.id}>
          <div>
            {edycja?.id === h.id ? (
              <form onSubmit={zapiszEdycje} className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                <input aria-label="Nazwa nawyku" value={edycja.name} maxLength={200} required
                  onChange={(ev) => setEdycja({ ...edycja, name: ev.target.value })} />
                <input aria-label="Termin (dni)" inputMode="numeric" value={edycja.target_days} style={{ width: 70 }}
                  onChange={(ev) => setEdycja({ ...edycja, target_days: ev.target.value })} />
                <button type="submit" className="btn btn--small" disabled={busy === h.id}>Zapisz</button>
                <button type="button" className="btn btn--ghost btn--small" onClick={() => setEdycja(null)}>Anuluj</button>
              </form>
            ) : (
              <>
                <b>{h.name}</b>
                <div className="meta">{h.progress_label} · {dniTekst(h.days_of_week)}</div>
                {h.author_note && <div className="meta">„{h.author_note}”</div>}
                {zarzadzanie && (
                  <div className="row" style={{ gap: 6, marginTop: 4 }}>
                    <button type="button" className="btn btn--ghost btn--small"
                      onClick={() => setEdycja({ id: h.id, name: h.name, target_days: String(h.target_days) })}>Edytuj</button>
                    <button type="button" className="btn btn--ghost btn--small" disabled={busy === h.id}
                      onClick={() => void archiwizuj(h)}>Usuń</button>
                  </div>
                )}
              </>
            )}
          </div>
          <div style={{ textAlign: "right" }}>
            {h.done_today ? (
              <button type="button" className="btn btn--ghost btn--small" disabled={busy === h.id}
                aria-label={`Cofnij odhaczenie: ${h.name}`} onClick={() => void odhacz(h)}>
                <span className="badge badge--ok">✓ dziś</span>
              </button>
            ) : (
              <button type="button" className="btn btn--small" disabled={busy === h.id || !h.scheduled_today}
                aria-label={`Odhacz na dziś: ${h.name}`} onClick={() => void odhacz(h)}>
                {busy === h.id ? "…" : h.scheduled_today ? "Wykonane" : "Dziś wolne"}
              </button>
            )}
          </div>
        </div>
      ))}

      {absolutoria.map((h) => h.ack_on ? (
        <div className="exercise" key={h.id}>
          <div><b>{h.name}</b><div className="meta">to już Twój nawyk — utrwalony {h.graduated_on}</div></div>
          <div style={{ textAlign: "right" }}>
            {zarzadzanie && <button type="button" className="btn btn--ghost btn--small" onClick={() => void archiwizuj(h)}>Ukryj</button>}
          </div>
        </div>
      ) : (
        <div className="card card--accent" key={h.id} role="region" aria-label={`Absolutorium: ${h.name}`} style={{ margin: "10px 0" }}>
          <b style={{ color: "var(--text)" }}><Icon name="trophy" /> {h.name} — gratulacje!</b>
          <p className="dim" style={{ margin: "4px 0 8px", fontSize: "0.9rem" }}>
            {h.target_days} dni za Tobą. Ta czynność stała się Twoim nawykiem — nie musisz jej już odhaczać. Aplikacja
            przestaje o nią pytać.
          </p>
          <div className="row" style={{ gap: 6 }}>
            <button type="button" className="btn btn--small" disabled={busy === h.id} onClick={() => void wymien(h)}>Wymień na nowy</button>
            <button type="button" className="btn btn--ghost btn--small" disabled={busy === h.id} onClick={() => void zostaw(h)}>Zostaw tak jak jest</button>
          </div>
        </div>
      ))}

      {zarzadzanie && !form && wolne > 0 && (
        <button type="button" className="btn btn--ghost btn--small" style={{ marginTop: 8 }} onClick={() => setForm({ ...PUSTY })}>
          + Dodaj nawyk ({wolne} {wolne === 1 ? "wolne miejsce" : "wolne miejsca"})
        </button>
      )}
      {zarzadzanie && wolne === 0 && !form && (
        <small className="dim" style={{ display: "block", marginTop: 8 }}>Trzy nawyki naraz to maksimum — usuń któryś, żeby dodać nowy.</small>
      )}
      {form && (
        <form onSubmit={dodaj} style={{ marginTop: 10 }} aria-label="Nowy nawyk">
          <label htmlFor="hab-name">Co chcesz utrwalić?</label>
          <input id="hab-name" required maxLength={200} value={form.name} placeholder="np. Szklanka wody po przebudzeniu"
            onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <div className="field-row" style={{ marginTop: 6 }}>
            <div>
              <span id="hab-dni-label" style={{ display: "block", fontSize: "0.85rem" }}>Dni</span>
              <div className="row" role="group" aria-labelledby="hab-dni-label" style={{ gap: 4, flexWrap: "wrap" }}>
                {DNI.map(([n, l]) => (
                  <button type="button" key={n} className="btn btn--ghost btn--small" aria-pressed={form.days.includes(n)}
                    onClick={() => setForm({ ...form, days: form.days.includes(n) ? form.days.filter((x) => x !== n) : [...form.days, n] })}>{l}</button>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="hab-target">Termin (dni, 14–254)</label>
              <input id="hab-target" inputMode="numeric" value={form.target_days} aria-describedby="hab-target-why"
                onChange={(e) => setForm({ ...form, target_days: e.target.value })} />
              <small id="hab-target-why" className="dim">Po tylu wykonanych dniach nawyk uznajemy za utrwalony (domyślnie 66).</small>
            </div>
          </div>
          {tryb === "trener" && (
            <>
              <label htmlFor="hab-note" style={{ marginTop: 6 }}>Notatka dla klienta (opcjonalnie)</label>
              <input id="hab-note" maxLength={500} value={form.author_note} onChange={(e) => setForm({ ...form, author_note: e.target.value })} />
            </>
          )}
          <div className="row" style={{ gap: 6, marginTop: 8 }}>
            <button type="submit" className="btn btn--small" disabled={busy === "form"}>Dodaj</button>
            <button type="button" className="btn btn--ghost btn--small" onClick={() => setForm(null)}>Anuluj</button>
          </div>
        </form>
      )}
    </div>
  );
}
