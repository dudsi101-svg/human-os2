// Wspólny komponent „Przepisz ze zdjęcia" (OCR).
//
// Jeden komponent obsługuje wszystkie trzy zastosowania (etykieta produktu,
// kartka z planem lub dietą, skan dokumentu) — różni je wyłącznie `purpose`
// i to, co widok zrobi z zatwierdzonym wynikiem.
//
// Zasady interfejsu:
// * podgląd zdjęcia STOI OBOK rozpoznanego tekstu — człowiek porównuje, a
//   nie wierzy na słowo;
// * tekst jest edytowalny przed zatwierdzeniem; nic nie zapisuje się samo;
// * stan zadania jest ogłaszany przez aria-live (P10), a wszystkie pola
//   mają powiązane etykiety (for/id);
// * „silnik niedostępny" i „tryb lokalny vs rozszerzony" są napisane
//   wprost — nigdy jako błąd techniczny;
// * zdjęcie jest kompresowane w przeglądarce (P11) do 1600 px, czyli
//   dokładnie tyle, ile widzi silnik na serwerze.

import { useEffect, useRef, useState } from "react";
import { api, isCancel } from "./api";
import { AuthImage, ErrorBox, Spinner } from "./components";
import { OCR_MAX_PX, compressImage } from "./imageCompress";
import {
  OcrPurpose,
  OcrStatusInfo,
  OcrTask,
  modeLabel,
  statusMessage,
} from "./ocrUtils";

/** Co ile pytamy o stan zadania. Kolejka jest jednoslotowa, więc częstsze
 * odpytywanie i tak niczego nie przyspieszy. */
const POLL_MS = 1500;
/** Bezpiecznik: po tylu próbach przestajemy odpytywać i pokazujemy stan. */
const POLL_MAX = 60;

export interface OcrCaptureProps {
  purpose: OcrPurpose;
  /** Podmiot danych, gdy zdjęcie dotyczy klienta (trener wgrywa w jego imieniu). */
  clientId?: string;
  /** Dokument, przy którym ma zostać zapisany tekst (purpose=DOKUMENT). */
  documentId?: string;
  /** Plik JUŻ wgrany do aplikacji (np. skan przy dokumencie) — można go
   * przepisać bez robienia nowego zdjęcia. */
  existingFileId?: string;
  existingFileLabel?: string;
  title?: string;
  hint?: string;
  /** Zatwierdzenie: widok decyduje, co zrobić z gotowym tekstem/propozycją.
   * Zwrócenie `true` zamyka panel. */
  onApprove: (task: OcrTask, text: string) => Promise<boolean> | boolean;
  onClose?: () => void;
  approveLabel?: string;
}

export default function OcrCapture({
  purpose,
  clientId,
  documentId,
  existingFileId,
  existingFileLabel = "Przepisz plik, który już jest w aplikacji",
  title = "Przepisz ze zdjęcia",
  hint,
  onApprove,
  onClose,
  approveLabel = "Zatwierdź",
}: OcrCaptureProps) {
  const [info, setInfo] = useState<OcrStatusInfo | null>(null);
  const [task, setTask] = useState<OcrTask | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<number | null>(null);
  const previewRef = useRef<string | null>(null);

  const query = clientId ? `?client_id=${encodeURIComponent(clientId)}` : "";
  useEffect(() => {
    api.get<OcrStatusInfo>(`/api/ocr/status${query}`)
      .then(setInfo)
      .catch((e) => { if (!isCancel(e)) setError((e as Error).message); });
  }, [query]);

  // Sprzątanie: podgląd (blob URL) i odpytywanie kończą się razem z panelem.
  useEffect(() => () => {
    if (pollRef.current) window.clearTimeout(pollRef.current);
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
  }, []);

  function poll(taskId: string, attempt = 0) {
    pollRef.current = window.setTimeout(async () => {
      try {
        const fresh = await api.get<OcrTask & { queue_depth?: number }>(
          `/api/ocr/tasks/${taskId}`
        );
        setTask(fresh);
        if (fresh.status === "DONE") {
          setText(fresh.text ?? "");
          setBusy(false);
          return;
        }
        if (fresh.status === "FAILED" || fresh.status === "CANCELLED") {
          setBusy(false);
          return;
        }
        if (attempt < POLL_MAX) poll(taskId, attempt + 1);
        else setBusy(false);
      } catch (e) {
        if (!isCancel(e)) setError((e as Error).message);
        setBusy(false);
      }
    }, POLL_MS);
  }

  /** Zlecenie zadania na PLIKU JUŻ ISTNIEJĄCYM w aplikacji. */
  async function startFromFile(fileId: string) {
    setError(null);
    setTask(null);
    setText("");
    setBusy(true);
    try {
      const created = await api.post<OcrTask & { queue_depth?: number }>(
        "/api/ocr/tasks",
        {
          file_id: fileId,
          purpose,
          client_id: clientId ?? null,
          document_id: documentId ?? null,
        }
      );
      setTask(created);
      poll(created.id);
    } catch (e) {
      if (!isCancel(e)) setError((e as Error).message);
      setBusy(false);
    }
  }

  /** Nowe zdjęcie: kompresja w przeglądarce, upload, potem zadanie. */
  async function start(file: File) {
    setError(null);
    setBusy(true);
    try {
      const compressed = await compressImage(file, OCR_MAX_PX);
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
      const url = URL.createObjectURL(compressed);
      previewRef.current = url;
      setPreview(url);
      const uploaded = await api.upload<{ id: string }>(
        `/api/files${query}`, compressed
      );
      await startFromFile(uploaded.id);
    } catch (e) {
      if (!isCancel(e)) setError((e as Error).message);
      setBusy(false);
    }
  }

  async function approve() {
    if (!task) return;
    setBusy(true);
    setError(null);
    try {
      const close = await onApprove(task, text);
      if (close) onClose?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function cancelTask() {
    if (task) {
      // Rezygnacja usuwa propozycję razem z rozpoznanym tekstem.
      try {
        await api.del(`/api/ocr/tasks/${task.id}`);
      } catch {
        /* Świadomie: nieudane sprzątnięcie nie może zablokować zamknięcia
         * panelu — zadanie i tak nic nie zapisało. */
      }
    }
    onClose?.();
  }

  const engineDown = info !== null && !info.engine_available;
  const message = statusMessage(task, info?.queue_depth ?? 0);

  return (
    <div className="card card--accent" style={{ marginTop: 10 }}>
      <div className="row row--between">
        <b>{title}</b>
        <button type="button" className="btn btn--ghost btn--small" onClick={cancelTask}>
          Zamknij
        </button>
      </div>
      {hint && <p className="dim" style={{ marginTop: 4 }}>{hint}</p>}

      {info === null && !error && <Spinner />}

      {engineDown && (
        <p className="dim" role="status" style={{ marginTop: 4 }}>
          <b>Silnik niedostępny.</b> {info?.engine_reason}
        </p>
      )}

      {info !== null && (
        <p className="dim" style={{ marginTop: 4, fontSize: "0.8rem" }}>
          {info.mode === "EXTENDED"
            ? "Zdjęcie zostanie przepisane w trybie rozszerzonym (dokładniejszym), "
              + "bo masz aktywną zgodę na funkcje AI."
            : info.mode_reason}
        </p>
      )}

      <label htmlFor={`ocr-file-${purpose}`}>Zdjęcie (możesz zrobić je teraz)</label>
      <input
        id={`ocr-file-${purpose}`}
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        disabled={busy || engineDown}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void start(file);
          e.target.value = "";
        }}
      />

      {existingFileId && (
        <div className="row" style={{ marginTop: 6 }}>
          <button type="button" className="btn btn--ghost btn--small"
            disabled={busy || engineDown} onClick={() => startFromFile(existingFileId)}>
            {existingFileLabel}
          </button>
        </div>
      )}

      <p className="dim" role="status" aria-live="polite" style={{ marginTop: 6 }}>
        {message}
      </p>
      <ErrorBox error={error} />

      {(preview || task) && (
        <div className="field-row" style={{ marginTop: 8 }}>
          <div>
            <span className="meta">Zdjęcie</span>
            {preview ? (
              <img
                src={preview}
                alt="Zdjęcie do przepisania — porównaj z tekstem obok"
                style={{ width: "100%", borderRadius: 8, marginTop: 4 }}
              />
            ) : (
              existingFileId && (
                <AuthImage fileId={existingFileId}
                  alt="Plik do przepisania — porównaj z tekstem obok" />
              )
            )}
          </div>
          <div>
            <label htmlFor={`ocr-text-${purpose}`}>
              Rozpoznany tekst — popraw przed zatwierdzeniem
            </label>
            <textarea
              id={`ocr-text-${purpose}`}
              rows={12}
              value={text}
              disabled={task?.status !== "DONE"}
              onChange={(e) => setText(e.target.value)}
            />
            {task?.status === "DONE" && (
              <p className="dim" style={{ fontSize: "0.78rem" }}>
                Propozycja z rozpoznania ({modeLabel(task.engine)}). Nic nie
                zostało jeszcze zapisane — zapisuje dopiero Twoje zatwierdzenie.
                {task.mode_reason ? ` ${task.mode_reason}` : ""}
              </p>
            )}
          </div>
        </div>
      )}

      <div className="row" style={{ marginTop: 10, flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn"
          disabled={busy || task?.status !== "DONE" || !text.trim()}
          onClick={approve}
        >
          {approveLabel}
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--small"
          disabled={busy || engineDown}
          onClick={() => inputRef.current?.click()}
        >
          {task ? "Zrób zdjęcie jeszcze raz" : "Wybierz zdjęcie"}
        </button>
        <button type="button" className="btn btn--ghost btn--small" onClick={cancelTask}>
          Anuluj
        </button>
      </div>
    </div>
  );
}
