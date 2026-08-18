import { useEffect, useState } from "react";
import { api } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { TrainingPlan } from "../../types";
import PlanEditor from "./PlanEditor";

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

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!templates) return <div className="page"><Spinner /></div>;

  return (
    <div className="page page--wide">
      <TopBar title="Szablony planów" />
      {!creating && (
        <button className="btn btn--small" style={{ marginBottom: 10 }}
          onClick={() => setCreating(true)}>+ Nowy szablon</button>
      )}
      {creating && (
        <PlanEditor clientId={null} existingPlan={null} onSaved={load}
          onCancel={() => setCreating(false)} />
      )}
      {templates.map((t) => (
        <div className="card" key={t.id}>
          <div className="row row--between">
            <h3>{t.title}</h3>
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
    </div>
  );
}
