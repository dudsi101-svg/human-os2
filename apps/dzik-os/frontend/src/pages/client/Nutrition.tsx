import DietaSzablon from "./DietaSzablon";
import ZapotrzebowanieKarta from "../wywiad/Zapotrzebowanie";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getUser } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, FileDownloadButton, Icon, Spinner, TopBar } from "../../components";
import { NutritionVersion } from "../../types";
import { Dlaczego } from "../../wiedza/Dlaczego";

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

  const plan = plans?.find((p) => p.status === "ACTIVE") ?? plans?.[0] ?? null;
  const v = plan?.current_version ?? null;
  const [ostatniaZmiana, setOstatniaZmiana] = useState<string | null>(null);
  // Dieta z szablonu zastępuje ręczny plan — komunikat o braku planu tylko, gdy nie ma żadnej.
  const [dietaZSzablonu, setDietaZSzablonu] = useState(false);
  useEffect(() => {
    if (!plan) return;
    api.get<{ changes: { id: string }[] }>(`/api/plany/nutrition/${plan.id}/zmiany`)
      .then((d) => setOstatniaZmiana(d.changes[0]?.id ?? null)).catch(() => setOstatniaZmiana(null));
  }, [plan?.id, plan?.current_version_no]); // eslint-disable-line react-hooks/exhaustive-deps

  const load = () => {
    setError(null);
    api.get<{ plans: NutritionPlanRow[] }>(`/api/clients/${user.id}/nutrition`)
      .then((d) => setPlans(d.plans))
      .catch((e) => setError(e.message));
  };
  useEffect(() => { load(); }, [user.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (plan && showHistory && !versions) {
      api.get<{ versions: NutritionVersion[] }>(`/api/nutrition/${plan.id}/versions`)
        .then((d) => setVersions(d.versions))
        .catch((e) => setError(e.message));
    }
  }, [plan, showHistory, versions]);

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!plans) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dieta" />
      {/* Szablony diet ze skalowaniem (0.60.0): sekcja pojawia się tylko, gdy
          moduł jest włączony i trener przypisał dietę z szablonu. */}
      {/* Zapotrzebowanie kaloryczne (0.62.0): wynik z wywiadu albo zaproszenie do wypełnienia. */}
      <ZapotrzebowanieKarta clientId={user.id} tryb="klient" linkDoWywiadu="/wywiad?typ=zapotrzebowanie" kompakt />
      <DietaSzablon onStan={setDietaZSzablonu} />
      {!v && !dietaZSzablonu && <p className="dim">Trener nie dodał jeszcze planu żywieniowego.</p>}
      {plan && v && (
        <>
          <div className="row row--between">
            <div>
              <b>{plan.title}</b>
              <div><small>wersja {v.version_no} · {plDate(v.created_at)}
                {ostatniaZmiana && <> · <Link to={`/zmiany/${ostatniaZmiana}`}>Zobacz zmiany</Link></>}</small></div>
            </div>
            <button className="btn btn--ghost btn--small" aria-expanded={showHistory}
              onClick={() => setShowHistory(!showHistory)}>
              {showHistory ? "Ukryj historię" : "Historia wersji"}
            </button>
          </div>
          {showHistory && versions && (
            <div className="card" style={{ marginTop: 10 }}>
              <h2>Historia wersji</h2>
              <div className="table-wrap">
                <table className="simple table--cards">
                  <thead><tr><th>Wersja</th><th>Data</th><th>Powód</th></tr></thead>
                  <tbody>
                    {versions.slice().reverse().map((hv) => (
                      <tr key={hv.id}>
                        <td data-label="Wersja">v{hv.version_no}</td>
                        <td data-label="Data">{plDate(hv.created_at)}</td>
                        <td data-label="Powód">{hv.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div className="card" style={{ marginTop: 10 }}>
            <h2>Cele dzienne</h2>
            <div className="stat-grid">
              <div className="stat"><b>{v.content.kcal ?? "—"}</b><span>kcal</span></div>
              <div className="stat"><b>{v.content.protein_g ?? "—"} g</b><span>białko</span></div>
              <div className="stat"><b>{v.content.carbs_g ?? "—"} g</b><span>węglowodany</span></div>
              <div className="stat"><b>{v.content.fat_g ?? "—"} g</b><span>tłuszcze</span></div>
            </div>
            {/* Wiedza (0.56.0): uzasadnienie celu = zapisana decyzja trenera
                przy tej wersji diety; Wiedza niczego nie przelicza. */}
            <div className="row" style={{ marginTop: 10 }}>
              <Dlaczego etykieta="Dlaczego tyle kalorii?" naglowek="Cel kaloryczny"
                cel={{ plan_kind: "nutrition", plan_id: plan.id, plan_revision: v.version_no,
                  target_type: "energy_target", target_id: "plan" }} />
              <Dlaczego etykieta="Dlaczego takie makro?" naglowek="Makroskładniki"
                cel={{ plan_kind: "nutrition", plan_id: plan.id, plan_revision: v.version_no,
                  target_type: "macro_target", target_id: "plan" }} />
            </div>
          </div>
          {v.content.sections.map((s, i) => (
            <div className="card" key={i}>
              <h2>{s.title}</h2>
              <p style={{ whiteSpace: "pre-wrap", margin: 0 }}>{s.body}</p>
            </div>
          ))}
          {v.content.meals.length > 0 && (
            <div className="card">
              <h2>{v.content.kulinaria ? "Menu z kreatora dań" : "Przykładowe posiłki"}</h2>
              {v.content.kulinaria?.mode === "preview" && (
                <p className="dim" style={{ marginTop: 0, fontSize: "0.85rem" }}>
                  Podgląd kulinarny: receptury są szkicami bez testu kuchennego i bez policzonych
                  wartości odżywczych — posiłki nie mają kalorii ani makro, a cele dzienne nie
                  zostały sprawdzone względem tego menu.
                </p>
              )}
              {v.content.meals.map((m, i) => (
                <div className="exercise" key={i}>
                  <div style={{ width: "100%" }}>
                    <div className="row row--between">
                      <b>{m.name}</b>
                      {m.draft && <span className="badge badge--warn">szkic</span>}
                    </div>
                    {m.description && <div className="meta">{m.description}</div>}
                    {m.swaps && <div className="meta"><Icon name="swap" size={14} label="zamienniki" /> {m.swaps}</div>}
                    {/* Kreator dań (0.57.0): ślad wyboru dania zapisany razem z wersją
                        planu — panel pokazuje zapisaną decyzję, nie generuje powodu. */}
                    {m.trace_target && (
                      <div className="row" style={{ marginTop: 6 }}>
                        <Dlaczego etykieta="Dlaczego to danie?" naglowek="Wybór dania"
                          cel={{ plan_kind: "nutrition", plan_id: plan.id, plan_revision: v.version_no,
                            target_type: "meal", target_id: m.trace_target }} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {v.content.kulinaria && v.content.kulinaria.shopping_list.length > 0 && (
                <details style={{ marginTop: 8 }}>
                  <summary>Lista zakupów ({v.content.kulinaria.shopping_list.length} pozycji)</summary>
                  <ul style={{ fontSize: "0.85rem", paddingLeft: 18 }}>
                    {v.content.kulinaria.shopping_list.map((z) => (
                      <li key={z.food_id}>{z.name} — {Math.round(z.edible_grams)} g ({z.state})</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
          {v.content.supplements.length > 0 && (
            <div className="card">
              <h2>Suplementacja</h2>
              <p className="dim" style={{ marginTop: 0, fontSize: "0.85rem" }}>
                Zalecenia zapisane przez trenera w wersji {v.version_no} planu.
                Każda zmiana dawki zostaje w historii wersji.
              </p>
              {v.content.supplements.map((s, i) => (
                <div className="exercise" key={i}>
                  <div style={{ width: "100%" }}>
                    <div className="row row--between">
                      <b>{s.name}{s.form ? ` · ${s.form}` : ""}</b>
                      <span className="badge badge--accent">{s.dose}</span>
                    </div>
                    <div className="meta">Kiedy: {s.timing}</div>
                    <div className="meta">Po co: {s.purpose}</div>
                    {s.duration && <div className="meta">Okres: {s.duration}</div>}
                    <div className="meta">
                      Podstawa zalecenia: {s.source}
                      {s.specialist_consulted && " · konsultowane ze specjalistą"}
                    </div>
                    {s.notes && (
                      <div className="meta" style={{ whiteSpace: "pre-wrap" }}>
                        Uwagi: {s.notes}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div className="alert alert--info" style={{ marginTop: 10 }}>
                Suplementy to nie leki i nie zastępują diety ani leczenia.
                Trener personalny nie stawia diagnoz. Przed zmianą lub
                rozpoczęciem suplementacji skonsultuj się z lekarzem lub
                dietetykiem — zwłaszcza przy chorobach, lekach, ciąży
                i karmieniu. Zgłoś trenerowi każdą alergię i nietolerancję;
                w razie niepokojących objawów przerwij i skontaktuj się
                z lekarzem.
              </div>
            </div>
          )}
          {v.document_file_id && (
            <div className="card">
              {/* Chroniony plik — pobieranie wyłącznie przez uwierzytelnione
                  API (zwykły link nie wysyła autoryzacji). */}
              <FileDownloadButton fileId={v.document_file_id}
                label={<><Icon name="download" size={16} /> Pobierz dietę (PDF)</>}
                className="btn btn--small" />
            </div>
          )}
        </>
      )}
    </div>
  );
}
