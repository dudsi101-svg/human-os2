import { useEffect, useState } from "react";
import { api } from "../../api";
import { ErrorBox, Spinner } from "../../components";
import { ile } from "../../plural";
import { BuiltinPlanTemplate, PlanDay, ProgressionModel } from "../../types";

/**
 * Gotowe schematy treningowe — wbudowany katalog do jednorazowego importu.
 *
 * Import tworzy KOPIĘ w bibliotece trenera (zasada „Szablon ≠ plan klienta"),
 * więc późniejsze przeróbki niczego nie nadpisują w katalogu. Schemat jest
 * punktem startowym: trener dostosowuje go do klienta, sprzętu i tolerancji.
 */

type Katalog = {
  templates: BuiltinPlanTemplate[];
  progressions: Record<string, ProgressionModel>;
};

type Podglad = BuiltinPlanTemplate & { days: PlanDay[] };

export default function BuiltinTemplates({ onImported }: { onImported: () => void }) {
  const [katalog, setKatalog] = useState<Katalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [otwarty, setOtwarty] = useState<Podglad | null>(null);
  const [ladujePodglad, setLadujePodglad] = useState<string | null>(null);
  const [importuje, setImportuje] = useState<string | null>(null);
  const [komunikat, setKomunikat] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<Katalog>("/api/coach/plan-templates")
      .then(setKatalog)
      .catch((e) => setError(e.message));
  };
  useEffect(load, []);

  const pokaz = (id: string) => {
    if (otwarty?.id === id) { setOtwarty(null); return; }
    setLadujePodglad(id);
    api.get<Podglad>(`/api/coach/plan-templates/${id}`)
      .then(setOtwarty)
      .catch((e) => setError(e.message))
      .finally(() => setLadujePodglad(null));
  };

  const importuj = (t: BuiltinPlanTemplate) => {
    setImportuje(t.id);
    setKomunikat(null);
    api.post<{ days: number; exercises: number; linked_exercises: number }>(
      `/api/coach/plan-templates/${t.id}/import`, {},
    )
      .then((r) => {
        const bezLinku = r.exercises - r.linked_exercises;
        setKomunikat(
          `Dodano „${t.name}" do Twoich szablonów: ` +
          `${ile(r.days, "jednostka", "jednostki", "jednostek")}, ` +
          `${ile(r.exercises, "ćwiczenie", "ćwiczenia", "ćwiczeń")}.` +
          (bezLinku > 0
            ? ` ${ile(bezLinku, "pozycja", "pozycje", "pozycji")} nie ma jeszcze` +
              " karty w Twojej bazie ćwiczeń — możesz je podpiąć w edytorze planu."
            : ""),
        );
        onImported();
      })
      .catch((e) => setError(e.message))
      .finally(() => setImportuje(null));
  };

  if (error) return <ErrorBox error={error} onRetry={load} />;
  if (!katalog) return <Spinner />;

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Gotowe schematy</h2>
      <p className="dim" style={{ fontSize: "0.88rem", marginTop: 0 }}>
        {katalog.templates.length} sprawdzonych planów treningowych. Import robi
        z wybranego schematu <b>Twój</b> szablon — możesz go dowolnie zmieniać,
        a katalog zostaje nietknięty. Każde ćwiczenie ma własną zasadę
        progresji; aplikacja niczego nie podnosi sama, decyzję podejmujesz Ty.
      </p>

      {komunikat && (
        <div className="alert alert--info" role="status">{komunikat}</div>
      )}

      {katalog.templates.map((t) => (
        <div key={t.id} className="exercise">
          <div className="row row--between">
            <div>
              <b>{t.name}</b>
              <div className="meta">
                {[t.level, t.goal, `${t.days_per_week}× w tyg.`, `${t.duration_min} min`]
                  .join(" · ")}
              </div>
            </div>
            <div className="row" style={{ gap: 6 }}>
              <button className="btn btn--small btn--ghost" onClick={() => pokaz(t.id)}
                disabled={ladujePodglad === t.id}>
                {otwarty?.id === t.id ? "Zwiń" : ladujePodglad === t.id ? "…" : "Podgląd"}
              </button>
              <button className="btn btn--small" onClick={() => importuj(t)}
                disabled={importuje === t.id}>
                {importuje === t.id ? "Dodaję…" : "Dodaj do moich"}
              </button>
            </div>
          </div>
          <div className="meta">{t.description}</div>

          {otwarty?.id === t.id && (
            <div style={{ marginTop: 10 }}>
              <div className="meta"><b>Podział:</b> {t.split}</div>
              <div className="meta"><b>Docelowy RIR:</b> {t.target_rir} · <b>Intensywność:</b> {t.intensity}</div>
              <div className="meta" style={{ marginBottom: 8 }}><b>Deload:</b> {t.deload}</div>
              {otwarty.days.map((d, i) => (
                <div key={i} style={{ marginTop: 8 }}>
                  <b>{d.name}</b>
                  {d.exercises.map((ex, j) => {
                    const model = ex.progression
                      ? katalog.progressions[ex.progression]
                      : undefined;
                    return (
                      <div className="exercise" key={j}>
                        <div>{ex.name}</div>
                        <div className="meta">
                          {[
                            ex.sets && `${ex.sets}×${ex.reps ?? "?"}`,
                            ex.target_rir && `RIR ${ex.target_rir}`,
                            ex.rest && `przerwa ${ex.rest}`,
                            ex.tempo && `tempo ${ex.tempo}`,
                          ].filter(Boolean).join(" · ")}
                        </div>
                        {model && (
                          <div className="meta"><b>{model.name}:</b> {model.action}</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
