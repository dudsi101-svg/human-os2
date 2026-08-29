import { useEffect, useState } from "react";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, SheetImportPanel, Spinner, TopBar } from "../../components";
import { TrainingPlan } from "../../types";
import BuiltinTemplates from "./BuiltinTemplates";
import PlanEditor from "./PlanEditor";
import DietTemplatesTab from "./DietTemplates";

export default function Templates() {
  const [templates, setTemplates] = useState<TrainingPlan[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = () => {
    setCreating(false);
    api.get<{ templates: TrainingPlan[] }>("/api/plans/templates")
      .then((d) => setTemplates(d.templates))
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);

  // Zakładka Dieta (0.54.0): szablony diety żyją obok treningowych —
  // jeden ekran „Szablony", dwie zakładki, wybór trzymany lokalnie.
  const [tab, setTab] = useState<"TRENING" | "DIETA">("TRENING");

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!templates) return <div className="page"><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Szablony" />
      <div className="row" role="tablist" aria-label="Rodzaj szablonów"
        style={{ gap: 6, marginBottom: 12 }}>
        {(["TRENING", "DIETA"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k}
            className={`btn btn--small ${tab === k ? "" : "btn--ghost"}`}
            onClick={() => setTab(k)}>
            {k === "TRENING" ? "Trening" : "Dieta"}
          </button>
        ))}
      </div>
      {tab === "DIETA" && <DietTemplatesTab />}
      {tab === "TRENING" && (<>
      {!creating && (
        <AddTemplate onManual={() => setCreating(true)} onImported={load} />
      )}
      {creating && (
        <PlanEditor clientId={null} existingPlan={null} onSaved={load}
          onCancel={() => setCreating(false)} />
      )}
      {templates.map((t) => (
        <div className="card" key={t.id}>
          <div className="row row--between">
            <h2>{t.title}</h2>
            <small>{plDate(t.current_version?.created_at ?? "")}</small>
          </div>
          {t.current_version?.content.days.map((d, i) => (
            <div key={i}>
              <b>{d.name}</b>
              {d.exercises.map((ex, j) => (
                <div className="exercise" key={j}>
                  <div>{ex.name}</div>
                  <div className="meta">{[ex.sets && `${ex.sets}×${ex.reps ?? "?"}`, ex.weight].filter(Boolean).join(" · ")}</div>
                </div>
              ))}
            </div>
          ))}
          <small className="dim">
            Aby użyć szablonu, otwórz klienta → Plan → Nowy plan i odtwórz
            układ (kopiowanie szablonu do klienta: zaplanowane w kolejnej wersji).
          </small>
        </div>
      ))}
      </>)}
    </div>
  );
}

/** Jedno miejsce „Dodaj szablon" zamiast trzech osobnych wejść.
 *
 * Wcześniej ekran otwierał się przyciskiem „Nowy szablon", kartą importu
 * z pliku i osobną kartą „Gotowe schematy" — trzy niezależne drogi obok
 * siebie, każda z własnym nagłówkiem. Ten sam gąszcz, który zakładka
 * Ćwiczenia miała do 0.34.0, i to samo lekarstwo: jedno pytanie, które
 * trener naprawdę ma w głowie — **skąd biorę ten szablon?** Widoczna jest
 * wyłącznie wybrana droga. Żadna nie została usunięta ani zmieniona.
 */
// Bez pola „hint": podpowiedź i tak pokazywałaby się dopiero PO wyborze
// drogi, a obie drogi z panelem opisują się same — dubel tekst w tekst
// (sprawdzone na ekranie, nie w wyobraźni).
const ADD_WAYS = [
  { key: "MANUAL", label: "Ułożę sam" },
  { key: "FILE", label: "Mam plik z szablonami" },
  { key: "BUILTIN", label: "Weź gotowy schemat" },
] as const;

type AddWay = (typeof ADD_WAYS)[number]["key"];

function AddTemplate({ onManual, onImported }: {
  onManual: () => void;
  onImported: () => void;
}) {
  const [way, setWay] = useState<AddWay | null>(null);

  function choose(next: AddWay) {
    // „Ułożę sam" prowadzi wprost do edytora — wybór od razu go otwiera,
    // zamiast pokazywać kolejny przycisk „no to teraz kliknij tutaj".
    if (next === "MANUAL") { setWay(null); onManual(); return; }
    setWay(way === next ? null : next);
  }

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <b>Dodaj szablon</b>
      <p className="dim" style={{ margin: "4px 0 8px" }}>
        Skąd bierzesz ten szablon?
      </p>
      <div className="row" role="group" aria-label="Sposób dodania szablonu"
        style={{ flexWrap: "wrap", gap: 6 }}>
        {ADD_WAYS.map((w) => (
          <button key={w.key} type="button" aria-pressed={way === w.key}
            className={`btn btn--small ${way === w.key ? "" : "btn--ghost"}`}
            onClick={() => choose(w.key)}>
            {w.label}
          </button>
        ))}
      </div>
      {way && (
        <>
          {way === "FILE" && (
            <SheetImportPanel
              kind="TEMPLATES"
              embedded
              title="Importuj szablony z pliku"
              description={
                <>
                  Wgraj gotowe szablony jako <b>CSV lub XLSX</b>: jeden wiersz to
                  jedno ćwiczenie w jednym dniu jednego szablonu. Nazwy ćwiczeń
                  dopasujemy do Twojej bazy — pozycja bez odpowiednika i tak
                  wejdzie do szablonu, tylko bez karty ćwiczenia. Szablon o tej
                  samej nazwie <b>nie jest nadpisywany</b>: dostaje nową wersję,
                  a poprzednia zostaje w historii. Najpierw raport, zapis to
                  osobne kliknięcie.
                </>
              }
              schemaUrl="/api/coach/plan-templates/import-schema"
              importUrl="/api/coach/plan-templates/import-file"
              exampleUrl="/api/coach/plan-templates/import-example"
              exportUrl="/api/coach/plan-templates/export-file"
              exampleFileName="dzik-os-szablony-wzor.csv"
              exportFileName="dzik-os-szablony.csv"
              onImported={onImported}
            />
          )}
          {way === "BUILTIN" && (
            <BuiltinTemplates embedded onImported={onImported} />
          )}
        </>
      )}
    </div>
  );
}
