import { useEffect, useState } from "react";
import { api, getUser } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, FileDownloadButton, Spinner, TopBar } from "../../components";
import { NutritionVersion } from "../../types";

interface NutritionPlanRow {
  id: string;
  title: string;
  status: string;
  current_version_no: number;
  current_version: NutritionVersion | null;
}

export default function Nutrition() {
  const user = getUser()!;
  const [plans, setPlans] = useState<NutritionPlanRow[] | null>(null);
  const [versions, setVersions] = useState<NutritionVersion[] | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const plan = plans?.[0] ?? null;
  const v = plan?.current_version ?? null;

  useEffect(() => {
    api.get<{ plans: NutritionPlanRow[] }>(`/api/clients/${user.id}/nutrition`)
      .then((d) => setPlans(d.plans))
      .catch((e) => setError(e.message));
  }, [user.id]);

  useEffect(() => {
    if (plan && showHistory && !versions) {
      api.get<{ versions: NutritionVersion[] }>(`/api/nutrition/${plan.id}/versions`)
        .then((d) => setVersions(d.versions))
        .catch((e) => setError(e.message));
    }
  }, [plan, showHistory, versions]);

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
  if (!plans) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dieta" />
      {!v && <p className="dim">Trener nie dodał jeszcze planu żywieniowego.</p>}
      {plan && v && (
        <>
          <div className="row row--between">
            <div>
              <b>{plan.title}</b>
              <div><small>wersja {v.version_no} · {plDate(v.created_at)}</small></div>
            </div>
            <button className="btn btn--ghost btn--small" onClick={() => setShowHistory(!showHistory)}>
              {showHistory ? "Ukryj historię" : "Historia wersji"}
            </button>
          </div>
          {showHistory && versions && (
            <div className="card" style={{ marginTop: 10 }}>
              <h3>Historia wersji</h3>
              <table className="simple">
                <thead><tr><th>Wersja</th><th>Data</th><th>Powód</th></tr></thead>
                <tbody>
                  {versions.slice().reverse().map((hv) => (
                    <tr key={hv.id}><td>v{hv.version_no}</td><td>{plDate(hv.created_at)}</td><td>{hv.reason}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="card" style={{ marginTop: 10 }}>
            <h3>Cele dzienne</h3>
            <div className="stat-grid">
              <div className="stat"><b>{v.content.kcal ?? "—"}</b><span>kcal</span></div>
              <div className="stat"><b>{v.content.protein_g ?? "—"} g</b><span>białko</span></div>
              <div className="stat"><b>{v.content.carbs_g ?? "—"} g</b><span>węglowodany</span></div>
              <div className="stat"><b>{v.content.fat_g ?? "—"} g</b><span>tłuszcze</span></div>
            </div>
          </div>
          {v.content.sections.map((s, i) => (
            <div className="card" key={i}>
              <h3>{s.title}</h3>
              <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{s.body}</p>
            </div>
          ))}
          {v.content.meals.length > 0 && (
            <div className="card">
              <h3>Przykładowe posiłki</h3>
              {v.content.meals.map((m, i) => (
                <div className="exercise" key={i}>
                  <div>
                    <b>{m.name}</b>
                    {m.description && <div className="meta">{m.description}</div>}
                    {m.swaps && <div className="meta">🔁 {m.swaps}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
          {v.document_file_id && (
            <div className="card">
              {/* Chroniony plik — pobieranie wyłącznie przez uwierzytelnione
                  API (zwykły link nie wysyła autoryzacji). */}
              <FileDownloadButton fileId={v.document_file_id}
                label="📄 Pobierz dietę (PDF)" className="btn btn--small" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
