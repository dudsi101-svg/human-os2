import { useEffect, useState } from "react";
import { api, getUser } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, Spinner, TopBar } from "../../components";
import { DocumentRow, ScheduleItem, CATEGORY_LABELS } from "../../types";
import { WEEKDAYS } from "../../dates";

export default function Documents() {
  const user = getUser()!;
  const [docs, setDocs] = useState<DocumentRow[] | null>(null);
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get<{ documents: DocumentRow[] }>(`/api/clients/${user.id}/documents`)
      .then((d) => setDocs(d.documents)).catch((e) => setError(e.message));
    api.get<{ items: ScheduleItem[] }>(`/api/clients/${user.id}/schedule`)
      .then((d) => setSchedule(d.items)).catch(() => undefined);
  }, [user.id]);

  async function openDoc(fileId: string) {
    const blob = await api.get<Blob>(`/api/files/${fileId}`);
    const url = URL.createObjectURL(blob);
    window.open(url, "_blank");
  }

  if (error) return <div className="page"><ErrorBox error={error} /></div>;
  if (!docs) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dokumenty i harmonogram" />
      <div className="card">
        <h3>Dokumenty od trenera</h3>
        {docs.length === 0 && <small>Brak dokumentów.</small>}
        {docs.map((d) => (
          <div className="exercise" key={d.id}>
            <div>
              <b>{d.title}</b>
              <div className="meta">{plDate(d.created_at)}</div>
            </div>
            <button className="btn btn--ghost btn--small" onClick={() => openDoc(d.file_id)}>
              Otwórz
            </button>
          </div>
        ))}
      </div>

      <div className="card">
        <h3>Pełny harmonogram</h3>
        {schedule.length === 0 && <small>Brak elementów harmonogramu.</small>}
        {schedule.map((s) => (
          <div className="exercise" key={s.id}>
            <div>
              <b>{s.name}</b> <span className="badge">{CATEGORY_LABELS[s.category] ?? s.category}</span>
              {s.instruction && <div className="meta">{s.instruction}</div>}
              {s.author_note && <div className="meta">ℹ️ {s.author_note}</div>}
              <div className="meta">
                {s.days_of_week.split(",").map((d) => WEEKDAYS[Number(d) - 1]).join(", ")}
                {s.time_of_day && ` · ${s.time_of_day}`}
                {s.status !== "ACTIVE" && ` · ${s.status === "PAUSED" ? "wstrzymane" : "zakończone"}`}
              </div>
            </div>
          </div>
        ))}
        <p className="dim" style={{ fontSize: "0.78rem", marginBottom: 0 }}>
          Każdy element harmonogramu ma zapisanego autora. Aplikacja tylko
          przypomina o planie wprowadzonym przez człowieka — nigdy sama nie
          ustala ani nie zmienia dawek.
        </p>
      </div>
    </div>
  );
}
