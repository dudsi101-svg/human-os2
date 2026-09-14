import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { ErrorBox } from "../../components";
import {
  BlocksApplied,
  domyslneDni,
  etykietaBloku,
  komunikatPoPrzypisaniu,
  podsumowaniePrzypisania,
} from "../../bloki";
import { BLOCK_KIND_LABELS, BLOCK_KINDS, BlockKind, ExerciseBlockRow, TrainingPlan } from "../../types";

/**
 * Karta „Przypisz plan” (0.76.0, „bloki jak szablony”) w karcie klienta → Plan:
 * szablon treningowy ALBO „bez szablonu — tylko bloki”, plus do trzech bloków
 * (rozgrzewka / aeroby / rozciąganie — po jednym na rodzaj) dokładanych do
 * każdego dnia. Szablon bez bloków = dokładnie dotychczasowe „Kopiuj do klienta”
 * (`copy-to` bez ciała). Nic nie jest zapisywane przed „Przypisz klientowi”.
 */

const BLOKI_API = "/api/coach/exercise-blocks";
const OPIS_RODZAJU: Record<BlockKind, string> = {
  WARMUP: "na początek każdego dnia",
  CARDIO: "po ćwiczeniach siłowych",
  STRETCH: "na koniec każdego dnia",
};

export default function PrzypiszPlan({ clientId, templates, onDone }: {
  clientId: string; templates: TrainingPlan[]; onDone: () => void;
}) {
  const [zrodlo, setZrodlo] = useState<"szablon" | "bloki">(templates.length ? "szablon" : "bloki");
  const [templateId, setTemplateId] = useState("");
  const [bloki, setBloki] = useState<ExerciseBlockRow[] | null>(null);
  const [wybor, setWybor] = useState<Record<BlockKind, string>>({ WARMUP: "", CARDIO: "", STRETCH: "" });
  const [title, setTitle] = useState("");
  const [dni, setDni] = useState("3");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ items: ExerciseBlockRow[] }>(BLOKI_API).then((d) => setBloki(d.items)).catch(() => setBloki([]));
  }, []);

  const aktywne = (kind: BlockKind) => (bloki ?? []).filter((b) => b.kind === kind && b.status === "ACTIVE");
  const wybrane = (kind: BlockKind) => (bloki ?? []).find((b) => b.id === wybor[kind]) ?? null;
  const szablon = templates.find((t) => t.id === templateId) ?? null;
  const idBlokow = BLOCK_KINDS.map((k) => wybor[k]).filter(Boolean);
  const liczbaDni = Math.max(1, Math.min(7, Number(dni) || 1));
  const gotowe = zrodlo === "szablon" ? !!szablon : idBlokow.length > 0 && title.trim().length > 0;
  const podsumowanie = gotowe ? podsumowaniePrzypisania({
    szablon: zrodlo === "szablon" ? szablon?.title ?? null : null,
    bloki: { WARMUP: wybrane("WARMUP"), CARDIO: wybrane("CARDIO"), STRETCH: wybrane("STRETCH") },
    dni: zrodlo === "szablon" ? szablon?.current_version?.content.days.length ?? null : liczbaDni,
  }) : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!gotowe) return;
    setBusy(true); setError(null); setNote(null);
    try {
      if (zrodlo === "szablon" && szablon) {
        // Bez bloków — dokładnie jak dotąd (bez ciała); z blokami — ciało z listą.
        const r = idBlokow.length
          ? await api.post<{ blocks_applied?: BlocksApplied }>(`/api/plans/${szablon.id}/copy-to/${clientId}`, { blocks: idBlokow })
          : await api.post<{ blocks_applied?: BlocksApplied }>(`/api/plans/${szablon.id}/copy-to/${clientId}`);
        setNote(`Przypisano szablon „${szablon.title}”. ` + (idBlokow.length
          ? komunikatPoPrzypisaniu(r.blocks_applied, szablon.current_version?.content.days.length ?? 0) : ""));
      } else {
        const r = await api.post<{ blocks_applied: BlocksApplied }>(`/api/clients/${clientId}/plans/from-blocks`, {
          title: title.trim(), days: domyslneDni(liczbaDni), blocks: idBlokow,
        });
        setNote(`Utworzono plan „${title.trim()}” z bloków. ` + komunikatPoPrzypisaniu(r.blocks_applied, liczbaDni));
      }
      setTemplateId(""); setWybor({ WARMUP: "", CARDIO: "", STRETCH: "" }); setTitle("");
      onDone();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" onSubmit={submit} data-testid="przypisz-plan">
      <fieldset className="list-editor" style={{ margin: 0 }}>
        <legend>Przypisz plan</legend>
        <p className="dim" style={{ fontSize: "0.85rem", margin: "0 0 6px" }}>
          Szablon treningowy albo same bloki; rozgrzewka, aeroby i rozciąganie trafiają do każdego dnia
          (dzień, który już ma blok danego rodzaju z szablonu, zostaje bez zmian).
        </p>
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}>
          <legend className="dim" style={{ fontSize: "0.85rem", padding: 0 }}>Podstawa planu</legend>
          <label className="row" style={{ alignItems: "center", minHeight: 44 }}>
            <input type="radio" name="pp-zrodlo" value="szablon" checked={zrodlo === "szablon"}
              disabled={templates.length === 0} onChange={() => setZrodlo("szablon")} />
            <span>Szablon treningowy{templates.length === 0 ? " (brak szablonów)" : ""}</span>
          </label>
          <label className="row" style={{ alignItems: "center", minHeight: 44 }}>
            <input type="radio" name="pp-zrodlo" value="bloki" checked={zrodlo === "bloki"} onChange={() => setZrodlo("bloki")} />
            <span>Bez szablonu — tylko bloki</span>
          </label>
        </fieldset>
        {zrodlo === "szablon" && (
          <>
            <label htmlFor="pp-szablon">Szablon</label>
            <select id="pp-szablon" value={templateId} aria-label="Wybierz szablon planu" onChange={(e) => setTemplateId(e.target.value)}>
              <option value="">— wybierz —</option>
              {templates.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </>
        )}
        {zrodlo === "bloki" && (
          <div className="field-row" style={{ marginTop: 6 }}>
            <div>
              <label htmlFor="pp-title">Nazwa planu</label>
              <input id="pp-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="np. Aeroby + rozciąganie" />
            </div>
            <div>
              <label htmlFor="pp-dni">Liczba dni (1–7)</label>
              <input id="pp-dni" type="number" inputMode="numeric" min={1} max={7} value={dni} onChange={(e) => setDni(e.target.value)} />
            </div>
          </div>
        )}
        {BLOCK_KINDS.map((kind) => {
          const lista = aktywne(kind);
          return (
            <div key={kind} style={{ marginTop: 6 }}>
              <label htmlFor={`pp-blok-${kind}`}>{BLOCK_KIND_LABELS[kind]} <span className="dim">({OPIS_RODZAJU[kind]})</span></label>
              {bloki !== null && lista.length === 0 ? (
                <p className="dim" style={{ fontSize: "0.85rem", margin: "2px 0 0" }} id={`pp-blok-${kind}`}>
                  Brak bloków tego rodzaju w katalogu — <Link to="/trener/szablony">Szablony → Bloki → „Dodaj wbudowane”</Link>.
                </p>
              ) : (
                <select id={`pp-blok-${kind}`} value={wybor[kind]} onChange={(e) => setWybor({ ...wybor, [kind]: e.target.value })}>
                  <option value="">bez</option>
                  {lista.map((b) => <option key={b.id} value={b.id}>{b.name} — {etykietaBloku(b)}</option>)}
                </select>
              )}
            </div>
          );
        })}
        {zrodlo === "bloki" && idBlokow.length === 0 && bloki !== null && (
          <p className="dim" style={{ fontSize: "0.85rem", marginTop: 6 }}>Wybierz co najmniej jeden blok.</p>
        )}
        {podsumowanie && (
          <p style={{ marginTop: 8 }} data-testid="pp-podsumowanie"><b>{podsumowanie}</b></p>
        )}
        <ErrorBox error={error} />
        <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }} data-testid="pp-status">{note ?? ""}</p>
        <div className="row" style={{ marginTop: 8, flexWrap: "wrap" }}>
          <button className="btn" disabled={busy || !gotowe}>{busy ? "Przypisywanie…" : "Przypisz klientowi"}</button>
        </div>
      </fieldset>
    </form>
  );
}
