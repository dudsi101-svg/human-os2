import { Suspense, lazy, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Icon, SheetImportPanel, Spinner, TopBar } from "../../components";
import { TrainingPlan } from "../../types";
import { odmien } from "../../plural";
import { KIND_BADGE, opisPozycji, rodzajPozycji } from "../../pozycje";
import { LinkKartyTrenera } from "../../opisCwiczenia";
import BuiltinTemplates from "./BuiltinTemplates";
import PlanEditor from "./PlanEditor";
import PublikacjaPanel from "./PublikacjaPanel";
import DietTemplatesTab from "./DietTemplates";
const BlokiTab = lazy(() => import("./BlokiTab"));

export default function Templates() {
  const [templates, setTemplates] = useState<TrainingPlan[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  // 0.75.0 (polecenie właściciela): lista pokazuje NAZWY, a treść szablonu
  // (dni, ćwiczenia, serie, uwagi, panel publikacji) rozwija się dopiero po
  // kliknięciu w nazwę. Stan rozwinięcia jest lokalny — nic nie zapisuje.
  const [rozwiniete, setRozwiniete] = useState<Set<string>>(new Set());
  const przelacz = (id: string) => setRozwiniete((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id); else next.add(id);
    return next;
  });

  const load = () => {
    setCreating(false);
    api.get<{ templates: TrainingPlan[] }>("/api/plans/templates")
      .then((d) => setTemplates(d.templates))
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);

  // Zakładka Dieta (0.54.0): szablony diety żyją obok treningowych —
  // jeden ekran „Szablony", dwie zakładki, wybór trzymany lokalnie.
  // Bloki rozgrzewki/rozciągania (0.73.0): trzecia zakładka, panel za React.lazy.
  const [tab, setTab] = useState<"TRENING" | "DIETA" | "BLOKI">("TRENING");
  // Szablony diet ze skalowaniem (0.60.0): link do panelu tylko, gdy moduł włączony.
  const [szablonyDiet, setSzablonyDiet] = useState(false);
  useEffect(() => {
    api.get<{ profiles: unknown[] }>("/api/diet/profiles").then(() => setSzablonyDiet(true)).catch(() => setSzablonyDiet(false));
  }, []);

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!templates) return <div className="page"><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Szablony" />
      <div className="row" role="tablist" aria-label="Rodzaj szablonów"
        style={{ gap: 6, marginBottom: 12 }}>
        {(["TRENING", "DIETA", "BLOKI"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={tab === k}
            className={`btn btn--small ${tab === k ? "" : "btn--ghost"}`}
            onClick={() => setTab(k)}>
            {k === "TRENING" ? "Trening" : k === "DIETA" ? "Dieta" : "Bloki"}
          </button>
        ))}
      </div>
      {tab === "DIETA" && szablonyDiet && (
        <div className="card" style={{ marginBottom: 10 }}>
          <div className="row row--between">
            <div><b>Szablony diet ze skalowaniem</b><div className="dim" style={{ fontSize: "0.85rem" }}>Profile, odsłony tygodnia, test skalowania 1400–3200 kcal, publikacja, import JSON.</div></div>
            <Link className="btn btn--small" to="/trener/szablony-diet">Otwórz panel</Link>
          </div>
        </div>
      )}
      {tab === "DIETA" && <DietTemplatesTab />}
      {tab === "BLOKI" && <Suspense fallback={<Spinner />}><BlokiTab /></Suspense>}
      {tab === "TRENING" && (<>
      {!creating && (
        <AddTemplate onManual={() => setCreating(true)} onImported={load} />
      )}
      {creating && (
        <PlanEditor clientId={null} existingPlan={null} onSaved={load}
          onCancel={() => setCreating(false)} />
      )}
      {templates.length === 0 && (
        <p className="dim">Nie masz jeszcze szablonów treningowych — dodaj pierwszy powyżej.</p>
      )}
      {templates.map((t) => {
        const dni = t.current_version?.content.days ?? [];
        const liczbaCwiczen = dni.reduce((s, d) => s + d.exercises.length, 0);
        const open = rozwiniete.has(t.id);
        const tresc = `szablon-tresc-${t.id}`;
        return (
        <div className="card" key={t.id} data-testid="szablon-karta">
          {/* Nagłówek = przycisk (h2 z przyciskiem w środku to wzorzec akordeonu:
              czytnik ekranu dostaje i poziom nagłówka, i stan rozwinięcia). */}
          <div className="row row--between" style={{ alignItems: "flex-start", gap: 8 }}>
            <h2 style={{ margin: 0, flex: 1 }}>
              <button type="button" className="knowledge-card__toggle" aria-expanded={open}
                aria-controls={tresc} onClick={() => przelacz(t.id)} data-testid="szablon-nazwa">
                <span>
                  <span style={{ fontSize: "1.1rem", fontWeight: 700 }}>{t.title}</span>
                  <span className="meta" style={{ display: "block", fontWeight: 400 }}>
                    {dni.length} {odmien(dni.length, "dzień", "dni", "dni")} · {liczbaCwiczen} {odmien(liczbaCwiczen, "pozycja", "pozycje", "pozycji")}
                    {t.current_version?.created_at ? ` · ${plDate(t.current_version.created_at)}` : ""}
                  </span>
                </span>
                <span className="dim"><Icon name={open ? "chevron-up" : "chevron-down"} size={18} /></span>
              </button>
            </h2>
          </div>
          {open && (
            <div id={tresc} style={{ marginTop: 8 }}>
              {dni.map((d, i) => (
                <div key={i}>
                  <b>{d.name}</b>
                  {d.exercises.map((ex, j) => (
                    <div className="exercise" key={j}>
                      <div>
                        {ex.name}
                        {KIND_BADGE[rodzajPozycji(ex)] && <span className="badge" style={{ marginLeft: 8 }}>{KIND_BADGE[rodzajPozycji(ex)]}</span>}
                        {rodzajPozycji(ex) === "strength" && <LinkKartyTrenera exerciseId={ex.exercise_id} />}
                        {ex.comment && <div className="meta">{ex.comment}</div>}
                      </div>
                      <div className="meta">{opisPozycji(ex)}</div>
                    </div>
                  ))}
                </div>
              ))}
              {/* 0.58.0: szablon jest edytowalny jak plan — szkic → sprawdź zmiany →
                  publikuj (bez powiadomienia, bo nie ma klienta); kopie u klientów
                  zostają nietknięte (pochodzenie zapisane na ich wersji v1). */}
              <PublikacjaPanel planKind="training" planId={t.id} clientId={null} onZmiana={load} />
              <small className="dim">
                Kopiowanie do klienta: karta klienta → Plan → „Z szablonu…”. Kopia jest
                niezależna: zmiany szablonu nie zmieniają planów klientów.
              </small>
            </div>
          )}
        </div>
        );
      })}
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
