import { useEffect, useState } from "react";
import { api, getUser } from "../../api";
import { plDate } from "../../dates";
import { ErrorBox, FileDownloadButton, Icon, Spinner, TopBar } from "../../components";
import { DocumentRow, ScheduleItem, CATEGORY_LABELS } from "../../types";
import OcrCapture from "../../OcrCapture";
import { documentMatches } from "../../ocrUtils";
import { WEEKDAYS } from "../../dates";

export default function Documents() {
  const user = getUser()!;
  const [docs, setDocs] = useState<DocumentRow[] | null>(null);
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  // Wyszukiwanie obejmuje tytuł ORAZ tekst przepisany ze skanu — po to on jest.
  const [query, setQuery] = useState("");
  // Który dokument właśnie przepisujemy (skan -> tekst przeszukiwalny).
  const [ocrDoc, setOcrDoc] = useState<DocumentRow | null>(null);
  const [ocrNote, setOcrNote] = useState<string | null>(null);

  const load = () => {
    setError(null);
    api.get<{ documents: DocumentRow[] }>(`/api/clients/${user.id}/documents`)
      .then((d) => setDocs(d.documents)).catch((e) => setError(e.message));
    // Harmonogram to druga sekcja tej strony — jego błąd też jest widoczny
    // (wcześniej znikał bez śladu).
    api.get<{ items: ScheduleItem[] }>(`/api/clients/${user.id}/schedule`)
      .then((d) => setSchedule(d.items))
      .catch((e) => setError(`Nie udało się wczytać harmonogramu. ${e.message}`));
  };
  useEffect(() => { load(); }, [user.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="page"><ErrorBox error={error} onRetry={load} /></div>;
  if (!docs) return <div className="page"><Spinner /></div>;

  return (
    <div className="page">
      <TopBar title="Dokumenty i harmonogram" />
      <div className="card">
        <h2>Dokumenty od trenera</h2>
        <label htmlFor="doc-search">Szukaj w dokumentach</label>
        <input id="doc-search" type="search" value={query}
          placeholder="tytuł albo słowo z przepisanego skanu"
          onChange={(e) => setQuery(e.target.value)} />
        <p className="dim" role="status" aria-live="polite" style={{ marginTop: 4 }}>
          {ocrNote
            ?? (query
              ? `Pasujących dokumentów: ${docs.filter((d) => documentMatches(d, query)).length}.`
              : "")}
        </p>
        {docs.length === 0 && <small>Brak dokumentów.</small>}
        {docs.filter((d) => documentMatches(d, query)).map((d) => (
          <div className="exercise" key={d.id} style={{ display: "block" }}>
            <div className="row row--between">
              <div>
                <b>{d.title}</b>
                <div className="meta">
                  {plDate(d.created_at)}
                  {d.ocr_text ? " · tekst przepisany ze zdjęcia" : ""}
                </div>
              </div>
              <FileDownloadButton fileId={d.file_id} openInTab label="Otwórz" />
            </div>
            {d.ocr_text && (
              <details style={{ marginTop: 6 }}>
                <summary>Przepisany tekst (do wyszukiwania)</summary>
                <p className="dim" style={{ whiteSpace: "pre-wrap" }}>{d.ocr_text}</p>
              </details>
            )}
            <div className="row" style={{ marginTop: 6 }}>
              <button type="button" className="btn btn--ghost btn--small"
                aria-expanded={ocrDoc?.id === d.id}
                onClick={() => setOcrDoc(ocrDoc?.id === d.id ? null : d)}>
                {d.ocr_text ? "Przepisz ponownie ze zdjęcia" : "Przepisz ze zdjęcia"}
              </button>
            </div>
            {ocrDoc?.id === d.id && (
              <OcrCapture
                purpose="DOKUMENT"
                documentId={d.id}
                existingFileId={d.file_id}
                existingFileLabel="Przepisz skan, który już jest w aplikacji"
                title={`Skan: ${d.title}`}
                hint={"Zrób zdjęcie dokumentu. Rozpoznany tekst zapiszemy przy "
                  + "dokumencie dopiero po Twoim zatwierdzeniu — oryginał pliku "
                  + "zostaje bez zmian."}
                approveLabel="Zapisz przepisany tekst"
                onApprove={async (task, text) => {
                  await api.post(`/api/ocr/tasks/${task.id}/approve`, { text });
                  setOcrNote("Zapisano przepisany tekst — dokument da się teraz wyszukać.");
                  setOcrDoc(null);
                  load();
                  return true;
                }}
                onClose={() => setOcrDoc(null)}
              />
            )}
          </div>
        ))}
      </div>

      <div className="card">
        <h2>Pełny harmonogram</h2>
        {schedule.length === 0 && <small>Brak elementów harmonogramu.</small>}
        {schedule.map((s) => (
          <div className="exercise" key={s.id}>
            <div>
              <b>{s.name}</b> <span className="badge">{CATEGORY_LABELS[s.category] ?? s.category}</span>
              {s.instruction && <div className="meta">{s.instruction}</div>}
              {s.author_note && <div className="meta"><Icon name="info" size={14} label="autor zalecenia" /> {s.author_note}</div>}
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
