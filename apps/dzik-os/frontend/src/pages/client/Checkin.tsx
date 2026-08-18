import { FormEvent, useEffect, useRef, useState } from "react";
import { api, getUser, isCancel, uploadFileWithProgress } from "../../api";
import { mondayOfWeek, plDate } from "../../dates";
import { ErrorBox, SectionLabel, Spinner, TopBar } from "../../components";
import { CheckinData, POSE_LABELS, ScaleAnswerState } from "../../types";

// Skale subiektywne z jawnym znaczeniem krańców — użytkownik widzi, co
// oznacza 1, a co 5, zanim cokolwiek wybierze.
const SCALES: { key: string; label: string; low: string; high: string }[] = [
  { key: "energy", label: "Energia", low: "1 = brak energii", high: "5 = pełna energia" },
  { key: "sleep", label: "Sen", low: "1 = bardzo słaby", high: "5 = bardzo dobry" },
  { key: "hunger", label: "Głód", low: "1 = brak głodu", high: "5 = bardzo silny głód" },
  { key: "stress", label: "Stres", low: "1 = bardzo niski", high: "5 = bardzo wysoki" },
  { key: "recovery", label: "Regeneracja", low: "1 = brak regeneracji", high: "5 = pełna regeneracja" },
  { key: "diet_adherence", label: "Realizacja diety", low: "1 = wcale", high: "5 = w pełni" },
];

/** Świadoma decyzja użytkownika dla jednej skali — BEZ wartości domyślnej.
 * Dopóki nie ma decyzji (undefined), raportu nie da się wysłać. */
type ScaleAnswer =
  | { state: "ANSWERED"; value: number }
  | { state: "SKIPPED" }
  | { state: "NOT_APPLICABLE" };

type PhotoPose = keyof typeof POSE_LABELS;

interface PhotoItem {
  localId: string;
  file: File;
  previewUrl: string;
  pose: PhotoPose;
  status: "PENDING" | "UPLOADING" | "DONE" | "ERROR";
  progress: number;
  fileId?: string;
  error?: string;
}

interface SubmitResult {
  id: string;
  revision: number;
  photos_attached: number;
  photos_expected: number | null;
  photos_complete: boolean;
}

const MAX_PHOTOS = 8; // ten sam limit egzekwuje backend (422)

/** Kompresja po stronie klienta PRZED wysłaniem: obrót zgodny z
 * orientacją EXIF (imageOrientation: "from-image"), maks. 2048 px dłuższego
 * boku, JPEG ~0.85. Przejście przez canvas naturalnie USUWA wszystkie
 * metadane EXIF (w tym GPS) — backendowy strip z P4 zostaje jako druga
 * warstwa (i jedyna, gdy kompresja się nie powiedzie i leci oryginał). */
async function compressImage(file: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
    const MAX_PX = 2048;
    const scale = Math.min(1, MAX_PX / Math.max(bitmap.width, bitmap.height));
    const w = Math.max(1, Math.round(bitmap.width * scale));
    const h = Math.max(1, Math.round(bitmap.height * scale));
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, w, h);
    bitmap.close();
    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, "image/jpeg", 0.85)
    );
    if (!blob) return file;
    const base = file.name.replace(/\.[^.]+$/, "") || "zdjecie";
    return new File([blob], `${base}.jpg`, { type: "image/jpeg" });
  } catch {
    // Świadomie: stara przeglądarka / uszkodzony plik — wysyłamy oryginał,
    // EXIF/GPS i rozdzielczość utnie backend (file_safety.process_image).
    return file;
  }
}

function newIdemKey(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `idem-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
  }
}

interface DraftShape {
  week: string;
  form: Record<string, string>;
  answers: Record<string, ScaleAnswer>;
  idemKey: string;
  photoCount: number;
}

const draftKey = (userId: string, week: string) => `dzik_checkin_draft_${userId}_${week}`;

export default function Checkin() {
  const user = getUser()!;
  const currentWeek = mondayOfWeek();
  const [checkins, setCheckins] = useState<CheckinData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [partial, setPartial] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<Record<string, ScaleAnswer>>({});
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [draftNotice, setDraftNotice] = useState<string | null>(null);
  const [idemKey, setIdemKey] = useState(newIdemKey);
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const restoredRef = useRef(false);

  const load = () =>
    api.get<{ checkins: CheckinData[] }>(`/api/clients/${user.id}/checkins`)
      .then((d) => setCheckins(d.checkins))
      .catch((e) => setError(e.message));
  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Wersja robocza: przywrócenie po błędzie/zamknięciu karty (localStorage).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(draftKey(user.id, currentWeek));
      if (raw) {
        const draft = JSON.parse(raw) as DraftShape;
        if (draft.week === currentWeek) {
          setForm(draft.form ?? {});
          setAnswers(draft.answers ?? {});
          if (draft.idemKey) setIdemKey(draft.idemKey);
          setDraftNotice(
            "Przywrócono wersję roboczą raportu."
            + (draft.photoCount > 0
              ? " Zdjęcia trzeba dodać ponownie (nie są zapisywane w wersji roboczej)."
              : "")
          );
        }
      }
    } catch {
      /* Świadomie: uszkodzony draft nie może zablokować formularza. */
    }
    restoredRef.current = true;
  }, [user.id, currentWeek]);

  useEffect(() => {
    if (!restoredRef.current) return;
    try {
      const draft: DraftShape = {
        week: currentWeek, form, answers, idemKey, photoCount: photos.length,
      };
      localStorage.setItem(draftKey(user.id, currentWeek), JSON.stringify(draft));
    } catch {
      /* Świadomie: pełny localStorage nie może wywrócić formularza. */
    }
  }, [form, answers, idemKey, photos.length, user.id, currentWeek]);

  // Zwolnienie podglądów przy odmontowaniu.
  useEffect(() => () => {
    setPhotos((list) => {
      list.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      return list;
    });
  }, []);

  const set = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));
  const setAnswer = (key: string, answer: ScaleAnswer) =>
    setAnswers((a) => ({ ...a, [key]: answer }));

  const updatePhoto = (localId: string, patch: Partial<PhotoItem>) =>
    setPhotos((list) => list.map((p) => (p.localId === localId ? { ...p, ...patch } : p)));

  async function addPhotos(files: File[]) {
    setError(null);
    const room = MAX_PHOTOS - photos.length;
    if (files.length > room) {
      setError(`Maksymalnie ${MAX_PHOTOS} zdjęć na raport.`);
    }
    for (const file of files.slice(0, Math.max(0, room))) {
      if (!file.type.startsWith("image/")) continue;
      const compressed = await compressImage(file);
      const item: PhotoItem = {
        localId: newIdemKey(),
        file: compressed,
        previewUrl: URL.createObjectURL(compressed),
        pose: "INNE",
        status: "PENDING",
        progress: 0,
      };
      setPhotos((list) => [...list, item]);
    }
  }

  function removePhoto(localId: string) {
    setPhotos((list) => {
      const item = list.find((p) => p.localId === localId);
      if (item) URL.revokeObjectURL(item.previewUrl);
      return list.filter((p) => p.localId !== localId);
    });
  }

  function movePhoto(localId: string, delta: -1 | 1) {
    setPhotos((list) => {
      const index = list.findIndex((p) => p.localId === localId);
      const target = index + delta;
      if (index < 0 || target < 0 || target >= list.length) return list;
      const next = list.slice();
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  interface UploadOutcome {
    failures: number;
    done: number;
    total: number;
    cancelled: boolean;
  }

  /** Wysyłka zdjęć po jednym: upload z postępem, natychmiastowe dopięcie do
   * raportu (stan częściowy jest trwały po stronie serwera), ponowienie
   * tylko nieudanych, anulowanie w dowolnym momencie. */
  async function uploadPhotos(checkinId: string, list: PhotoItem[]): Promise<UploadOutcome> {
    let failures = 0;
    let done = list.filter((p) => p.status === "DONE").length;
    cancelledRef.current = false;
    setUploading(true);
    try {
      for (const photo of list) {
        if (photo.status === "DONE") continue;
        if (cancelledRef.current) break;
        updatePhoto(photo.localId, { status: "UPLOADING", progress: 0, error: undefined });
        try {
          const ac = new AbortController();
          abortRef.current = ac;
          const uploaded = photo.fileId
            ? { id: photo.fileId }
            : await uploadFileWithProgress<{ id: string }>("/api/files", photo.file, {
              onProgress: (fraction) => updatePhoto(photo.localId, { progress: fraction }),
              signal: ac.signal,
            });
          updatePhoto(photo.localId, { fileId: uploaded.id });
          await api.post(`/api/checkins/${checkinId}/photos`, {
            photos: [{ file_id: uploaded.id, pose: photo.pose }],
          });
          updatePhoto(photo.localId, { status: "DONE", progress: 1 });
          done += 1;
        } catch (err) {
          if (isCancel(err)) {
            updatePhoto(photo.localId, { status: "PENDING", progress: 0 });
            cancelledRef.current = true;
            break;
          }
          failures += 1;
          updatePhoto(photo.localId, { status: "ERROR", error: (err as Error).message });
        }
      }
    } finally {
      abortRef.current = null;
      setUploading(false);
    }
    return { failures, done, total: list.length, cancelled: cancelledRef.current };
  }

  function clearAfterSuccess() {
    setPhotos((list) => {
      list.forEach((p) => URL.revokeObjectURL(p.previewUrl));
      return [];
    });
    setForm({});
    setAnswers({});
    setSubmittedId(null);
    setIdemKey(newIdemKey());
    try {
      localStorage.removeItem(draftKey(user.id, currentWeek));
    } catch {
      /* Świadomie: brak dostępu do localStorage nie zmienia wyniku wysyłki. */
    }
  }

  async function finishUploads(outcome: UploadOutcome) {
    await load();
    if (outcome.failures === 0 && !outcome.cancelled && outcome.done >= outcome.total) {
      setOk(
        outcome.total > 0
          ? "Raport wysłany w całości (razem ze zdjęciami). Trener odpowie w aplikacji."
          : "Raport wysłany. Trener odpowie w aplikacji."
      );
      setPartial(null);
      clearAfterSuccess();
    } else {
      setPartial(
        `Raport zapisany, ale zdjęcia nie są kompletne (wysłano ${outcome.done} z `
        + `${outcome.total}). Raport jest oznaczony jako częściowy — ponów `
        + "nieudane zdjęcia albo zakończ bez nich."
      );
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy || uploading) return; // blokada podwójnego wysłania
    const undecided = SCALES.filter((s) => !answers[s.key]);
    if (undecided.length > 0) {
      setError(
        "Każde pytanie wymaga świadomej decyzji — oceń albo oznacz jako "
        + `pominięte: ${undecided.map((s) => s.label).join(", ")}.`
      );
      return;
    }
    if (photos.length > MAX_PHOTOS) {
      setError(`Maksymalnie ${MAX_PHOTOS} zdjęć na raport.`);
      return;
    }
    setBusy(true);
    setError(null);
    setOk(null);
    setPartial(null);
    try {
      const scaleStates: Record<string, ScaleAnswerState> = {};
      const scaleValues: Record<string, number | null> = {};
      for (const s of SCALES) {
        const answer = answers[s.key]!;
        scaleStates[s.key] = answer.state;
        scaleValues[s.key] = answer.state === "ANSWERED" ? answer.value : null;
      }
      const attachedAlready = existing?.photos_attached ?? 0;
      const res = await api.post<SubmitResult>("/api/checkins", {
        week_start: currentWeek,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        trainings_done: form.trainings_done ? Number(form.trainings_done) : null,
        ...scaleValues,
        scale_states: scaleStates,
        pain_note: form.pain_note || null,
        comment: form.comment || null,
        questions: form.questions || null,
        photos_expected: attachedAlready + photos.length,
        idempotency_key: idemKey,
      });
      setSubmittedId(res.id);
      const outcome = await uploadPhotos(res.id, photos);
      await finishUploads(outcome);
    } catch (err) {
      // Błąd zapisu NIE czyści formularza — dane zostają (plus draft).
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function retryFailed() {
    if (!submittedId || uploading) return;
    setError(null);
    const outcome = await uploadPhotos(submittedId, photos);
    await finishUploads(outcome);
  }

  async function finishWithoutMissing(checkinId: string) {
    setError(null);
    try {
      // Serwer zna liczbę realnie dopiętych zdjęć — zamykamy deklarację
      // na tym poziomie (set_expected nie może zejść poniżej zapisanych).
      const fresh = await api.get<{ checkins: CheckinData[] }>(
        `/api/clients/${user.id}/checkins`
      );
      const row = fresh.checkins.find((c) => c.id === checkinId);
      await api.post(`/api/checkins/${checkinId}/photos`, {
        photos: [], set_expected: row?.photos_attached ?? 0,
      });
      setPartial(null);
      setOk("Raport zamknięty bez brakujących zdjęć.");
      clearAfterSuccess();
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  /** Dokończenie raportu częściowego z poprzedniej sesji (serwer pamięta
   * photos_expected; plików nie da się przywrócić — użytkownik dodaje je
   * ponownie i wysyła przez ten sam przepływ). */
  async function closeServerPartial(checkin: CheckinData) {
    setError(null);
    try {
      await api.post(`/api/checkins/${checkin.id}/photos`, {
        photos: [], set_expected: checkin.photos_attached,
      });
      setOk("Raport zamknięty bez brakujących zdjęć.");
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  if (!checkins) return <div className="page"><Spinner /></div>;
  const existing = checkins.find((c) => c.week_start === currentWeek);
  const locked = existing?.status === "REVIEWED";
  const serverPartial = existing && !existing.photos_complete;

  return (
    <div className="page">
      <TopBar title="Raport tygodniowy" />
      <form className="card" onSubmit={submit}>
        <div className="row row--between">
          <h3 style={{ margin: 0 }}>Tydzień od {plDate(currentWeek)}</h3>
          {existing && (
            <span className={`badge ${locked ? "badge--ok" : "badge--warn"}`}>
              {locked ? "oceniony" : serverPartial
                ? `częściowy · zdjęcia ${existing.photos_attached}/${existing.photos_expected}`
                : `rewizja ${existing.revision}`}
            </span>
          )}
        </div>
        {draftNotice && <p className="alert alert--info">{draftNotice}</p>}
        {locked && (
          <p className="alert alert--info">
            Ten tydzień został już oceniony — raport można wysłać w kolejnym tygodniu.
          </p>
        )}
        {existing && !locked && !serverPartial && (
          <p className="alert alert--info">
            Masz już raport za ten tydzień. Wysłanie ponownie zapisze poprawkę —
            poprzednia wersja zostaje w historii, a raport będzie oznaczony
            jako skorygowany.
          </p>
        )}
        {existing && !locked && serverPartial && (
          <div className="alert alert--error">
            Ten raport jest CZĘŚCIOWY: zapisano {existing.photos_attached} z{" "}
            {existing.photos_expected} zadeklarowanych zdjęć. Dodaj brakujące
            zdjęcia poniżej i wyślij ponownie, albo zamknij raport bez nich.
            <div style={{ marginTop: 6 }}>
              <button type="button" className="btn btn--ghost btn--small"
                onClick={() => closeServerPartial(existing)}>
                Zakończ bez brakujących zdjęć
              </button>
            </div>
          </div>
        )}

        <SectionLabel n={1} title="Ciało" />
        <div className="field-row">
          <div>
            <label>Masa ciała (kg)</label>
            <input type="number" step="0.1" min="0"
              value={form.weight_kg ?? ""}
              onChange={(e) => set("weight_kg", e.target.value)} />
          </div>
          <div>
            <label>Wykonane treningi</label>
            <input type="number" min="0" max="21"
              value={form.trainings_done ?? ""}
              onChange={(e) => set("trainings_done", e.target.value)} />
          </div>
        </div>

        <label>Zdjęcia sylwetki (opcjonalnie, maks. {MAX_PHOTOS})</label>
        <input type="file" accept="image/jpeg,image/png,image/webp" multiple
          disabled={uploading}
          onChange={(e) => {
            const files = Array.from(e.target.files ?? []);
            e.target.value = "";
            void addPhotos(files);
          }} />
        {photos.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <small className="dim">
              Zdjęcia są zmniejszane i czyszczone z metadanych (EXIF/GPS)
              na Twoim urządzeniu przed wysłaniem.
            </small>
            {photos.map((p, index) => (
              <PhotoRow key={p.localId} photo={p} index={index}
                count={photos.length} disabled={uploading}
                onPose={(pose) => updatePhoto(p.localId, { pose })}
                onRemove={() => removePhoto(p.localId)}
                onMove={(d) => movePhoto(p.localId, d)} />
            ))}
            {uploading && (
              <button type="button" className="btn btn--ghost btn--small"
                onClick={() => {
                  cancelledRef.current = true;
                  abortRef.current?.abort();
                }}>
                Przerwij wysyłanie zdjęć
              </button>
            )}
          </div>
        )}

        <SectionLabel n={2} title="Samopoczucie" />
        <p className="dim" style={{ fontSize: "0.82rem", marginTop: -4 }}>
          Żadne pytanie nie ma wartości domyślnej — wybierz ocenę świadomie
          albo oznacz pytanie jako pominięte. Tak dane pozostają prawdziwe.
        </p>
        {SCALES.map((s) => (
          <ScaleRow key={s.key} label={s.label} low={s.low} high={s.high}
            answer={answers[s.key]} disabled={locked || busy}
            onChange={(a) => setAnswer(s.key, a)} />
        ))}

        <SectionLabel n={3} title="Ból, urazy i pytania" />
        <label>Ból lub urazy (jeśli wystąpiły)</label>
        <textarea value={form.pain_note ?? ""}
          placeholder="Opisz dokładnie: gdzie, kiedy, przy jakim ruchu"
          onChange={(e) => set("pain_note", e.target.value)} />
        <label>Komentarz</label>
        <textarea value={form.comment ?? ""}
          onChange={(e) => set("comment", e.target.value)} />
        <label>Pytania do trenera</label>
        <textarea value={form.questions ?? ""}
          onChange={(e) => set("questions", e.target.value)} />

        <ErrorBox error={error} />
        {ok && <div className="alert alert--info">{ok}</div>}
        {partial && (
          <div className="alert alert--error">
            {partial}
            <div className="row" style={{ gap: 6, marginTop: 6 }}>
              <button type="button" className="btn btn--ghost btn--small"
                disabled={uploading} onClick={() => void retryFailed()}>
                Ponów nieudane zdjęcia
              </button>
              {submittedId && (
                <button type="button" className="btn btn--ghost btn--small"
                  disabled={uploading}
                  onClick={() => void finishWithoutMissing(submittedId)}>
                  Zakończ bez brakujących zdjęć
                </button>
              )}
            </div>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <button className="btn" disabled={busy || uploading || locked}>
            {busy || uploading
              ? "Wysyłanie…"
              : existing ? "Wyślij poprawkę" : "Wyślij raport"}
          </button>
        </div>
      </form>

      <h2>Poprzednie raporty</h2>
      {checkins.length === 0 && <p className="dim">Brak raportów.</p>}
      {checkins.map((c) => (
        <div className="card" key={c.id}>
          <div className="row row--between">
            <b>{plDate(c.week_start)}</b>
            <span className="row" style={{ gap: 4 }}>
              {c.corrected && (
                <span className="badge badge--warn">skorygowany</span>
              )}
              {!c.photos_complete && (
                <span className="badge badge--warn">
                  zdjęcia {c.photos_attached}/{c.photos_expected}
                </span>
              )}
              <span className={`badge ${c.status === "REVIEWED" ? "badge--ok" : "badge--warn"}`}>
                {c.status === "REVIEWED" ? "Oceniony" : "Wysłany"}
              </span>
            </span>
          </div>
          <small>
            {[
              c.payload.weight_kg != null && `masa ${c.payload.weight_kg} kg`,
              c.payload.trainings_done != null && `${c.payload.trainings_done} treningów`,
              c.revision > 1 && `rewizja ${c.revision}`,
            ].filter(Boolean).join(" · ")}
          </small>
          {c.coach_response && (
            <div className="alert alert--info" style={{ marginTop: 8 }}>
              <b>Odpowiedź trenera:</b> {c.coach_response}
              {c.rating != null && (
                <div style={{ marginTop: 4 }}>
                  <span className="badge badge--accent">Ocena raportu: {c.rating}/5</span>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ScaleRow({ label, low, high, answer, disabled, onChange }: {
  label: string;
  low: string;
  high: string;
  answer: ScaleAnswer | undefined;
  disabled: boolean;
  onChange: (a: ScaleAnswer) => void;
}) {
  const badge = !answer
    ? "—"
    : answer.state === "ANSWERED"
      ? `${answer.value}/5`
      : answer.state === "SKIPPED" ? "pominięte" : "nie dotyczy";
  return (
    <div className="scale-row">
      <div className="row row--between">
        <label style={{ margin: 0 }}>{label}</label>
        <span className={`badge ${answer ? "badge--accent" : ""}`}>{badge}</span>
      </div>
      <div className="row" style={{ gap: 4, marginTop: 6, flexWrap: "wrap" }}>
        {[1, 2, 3, 4, 5].map((n) => {
          const active = answer?.state === "ANSWERED" && answer.value === n;
          return (
            <button type="button" key={n} disabled={disabled}
              className="btn btn--ghost btn--small"
              style={active ? { background: "var(--accent)", color: "var(--accent-ink)" } : {}}
              onClick={() => onChange({ state: "ANSWERED", value: n })}>
              {n}
            </button>
          );
        })}
        <button type="button" disabled={disabled}
          className="btn btn--ghost btn--small"
          style={answer?.state === "SKIPPED" ? { borderColor: "var(--accent)" } : {}}
          onClick={() => onChange({ state: "SKIPPED" })}>
          Pomijam
        </button>
        <button type="button" disabled={disabled}
          className="btn btn--ghost btn--small"
          style={answer?.state === "NOT_APPLICABLE" ? { borderColor: "var(--accent)" } : {}}
          onClick={() => onChange({ state: "NOT_APPLICABLE" })}>
          Nie dotyczy
        </button>
      </div>
      <div className="scale-row__hint">{low} · {high}</div>
    </div>
  );
}

function PhotoRow({ photo, index, count, disabled, onPose, onRemove, onMove }: {
  photo: PhotoItem;
  index: number;
  count: number;
  disabled: boolean;
  onPose: (pose: PhotoPose) => void;
  onRemove: () => void;
  onMove: (delta: -1 | 1) => void;
}) {
  const statusLabel =
    photo.status === "DONE" ? "wysłane"
      : photo.status === "UPLOADING" ? `wysyłanie ${Math.round(photo.progress * 100)}%`
        : photo.status === "ERROR" ? "błąd" : "do wysłania";
  return (
    <div className="row" style={{ gap: 8, alignItems: "center", marginTop: 8 }}>
      <img src={photo.previewUrl} alt={`Zdjęcie ${index + 1}`}
        style={{ width: 56, height: 74, objectFit: "cover", borderRadius: 8 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="row row--between">
          <select value={photo.pose} disabled={disabled || photo.status === "DONE"}
            style={{ width: "auto" }}
            onChange={(e) => onPose(e.target.value as PhotoPose)}>
            {Object.entries(POSE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <span className={`badge ${photo.status === "DONE" ? "badge--ok"
            : photo.status === "ERROR" ? "badge--danger" : ""}`}>
            {statusLabel}
          </span>
        </div>
        {photo.status === "UPLOADING" && (
          <div style={{ background: "var(--bg-raised)", borderRadius: 999, height: 6, overflow: "hidden", marginTop: 4 }}>
            <div style={{ width: `${Math.round(photo.progress * 100)}%`, background: "var(--accent)", height: "100%" }} />
          </div>
        )}
        {photo.status === "ERROR" && photo.error && (
          <small role="alert" style={{ color: "var(--danger)" }}>{photo.error}</small>
        )}
      </div>
      {photo.status !== "DONE" && (
        <div className="row" style={{ gap: 4 }}>
          <button type="button" className="btn btn--ghost btn--small" title="Wyżej"
            disabled={disabled || index === 0} onClick={() => onMove(-1)}>↑</button>
          <button type="button" className="btn btn--ghost btn--small" title="Niżej"
            disabled={disabled || index === count - 1} onClick={() => onMove(1)}>↓</button>
          <button type="button" className="btn btn--ghost btn--small" title="Usuń"
            disabled={disabled} onClick={onRemove}>✕</button>
        </div>
      )}
    </div>
  );
}
