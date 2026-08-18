// Warstwa komunikacji z backendem. Frontend NIE podejmuje decyzji
// bezpieczeństwa — każde żądanie jest autoryzowane po stronie Core/backendu
// (kontrakt ADR-ARCH-003: UI -> Request -> Core -> Receipt -> UI).

import {
  classifyFetchFailure,
  errorTypeName,
  filenameFromDisposition,
  redactStack,
} from "./errorUtils";

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  must_change_password?: boolean;
  /** MFA aktywne na koncie (TOTP potwierdzone). */
  mfa_enabled?: boolean;
  /** Rola z obowiązkowym MFA bez konfiguracji — dostęp tylko do ekranu MFA. */
  mfa_setup_required?: boolean;
}

const TOKEN_KEY = "dzik_token";
const USER_KEY = "dzik_user";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function getUser(): SessionUser | null {
  const raw = sessionStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as SessionUser) : null;
}

export function setSession(token: string, user: SessionUser) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export class ApiError extends Error {
  status: number;
  /** Stabilny kod błędu z backendu (np. "NOT_FOUND", "VALIDATION_ERROR")
   * lub lokalny: "OFFLINE" / "TIMEOUT" / "CANCELLED". */
  code?: string;
  /** Identyfikator żądania (X-Request-Id) — do zgłoszenia problemu. */
  requestId?: string;
  constructor(status: number, detail: string, code?: string, requestId?: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

/** Anulowanie nieaktualnego żądania (zmiana widoku/parametru) — widoki mają
 * je IGNOROWAĆ, a nie pokazywać jako błąd. */
export function isCancel(error: unknown): boolean {
  return error instanceof ApiError && error.code === "CANCELLED";
}

export const OFFLINE_MESSAGE =
  "Brak połączenia z internetem. Dane wczytają się po odzyskaniu sieci.";
export const TIMEOUT_MESSAGE =
  "Serwer zbyt długo nie odpowiada. Sprawdź połączenie i spróbuj ponownie.";
export const SESSION_EXPIRED_MESSAGE =
  "Twoja sesja wygasła lub została zakończona. Zaloguj się ponownie — wrócisz do aplikacji.";

/** Limit czasu żądania: po tym czasie żądanie jest przerywane i widok
 * dostaje czytelny błąd z możliwością ponowienia (zamiast wiecznego spinnera). */
const REQUEST_TIMEOUT_MS = 20_000;

export interface RequestOpts {
  /** Sygnał anulowania z widoku — przerwane żądanie rzuca ApiError
   * z code="CANCELLED" (patrz isCancel). */
  signal?: AbortSignal;
}

/** fetch() z limitem czasu i klasyfikacją niepowodzeń bez odpowiedzi HTTP:
 * anulowanie przez widok (CANCELLED, status 0), timeout (TIMEOUT, status 0),
 * brak sieci (OFFLINE, status 0) — widoki pokazują polski komunikat
 * zamiast surowego "Failed to fetch" i wiecznego spinnera. */
async function fetchOrOffline(
  input: string,
  init: RequestInit,
  signal?: AbortSignal
): Promise<Response> {
  const timeout = new AbortController();
  const timer = setTimeout(() => timeout.abort(), REQUEST_TIMEOUT_MS);
  const onCallerAbort = () => timeout.abort();
  signal?.addEventListener("abort", onCallerAbort);
  try {
    return await fetch(input, { ...init, signal: timeout.signal });
  } catch {
    const kind = classifyFetchFailure(
      signal?.aborted === true,
      timeout.signal.aborted
    );
    const message =
      kind === "CANCELLED"
        ? "Żądanie anulowane"
        : kind === "TIMEOUT"
          ? TIMEOUT_MESSAGE
          : OFFLINE_MESSAGE;
    throw new ApiError(0, message, kind);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onCallerAbort);
  }
}

// --- Powrót do logowania po wygaśnięciu sesji -------------------------------
// Komunikat jest zapisywany PRZED przekierowaniem i pokazywany na ekranie
// logowania (consumeLoginNotice w Login.tsx) — użytkownik wie, co się stało.

const LOGIN_NOTICE_KEY = "dzik_login_notice";

function redirectToLogin(message: string) {
  clearSession();
  try {
    sessionStorage.setItem(LOGIN_NOTICE_KEY, message);
  } catch {
    /* Świadomie: pełny/zablokowany sessionStorage nie może zablokować
     * samego powrotu do logowania. */
  }
  if (!location.pathname.startsWith("/login")) location.assign("/login");
}

/** Czytelny powrót do logowania po wygaśnięciu sesji — dla warstw poza
 * request() (np. kanał SSE w realtime.ts, który sam dostaje 401 albo
 * zdarzenie session_expired). */
export function handleSessionExpired(): void {
  redirectToLogin(SESSION_EXPIRED_MESSAGE);
}

/** Jednorazowy komunikat dla ekranu logowania (np. „sesja wygasła"). */
export function consumeLoginNotice(): string | null {
  const value = sessionStorage.getItem(LOGIN_NOTICE_KEY);
  if (value) sessionStorage.removeItem(LOGIN_NOTICE_KEY);
  return value;
}

/** Wspólne odczytanie modelu błędu {detail, code, request_id} z odpowiedzi.
 * Frontend NIE pokazuje szczegółów technicznych — tylko detail (bezpieczny
 * polski komunikat z backendu) i ewentualnie request_id do zgłoszenia. */
async function errorFromResponse(resp: Response): Promise<ApiError> {
  let detail = `Błąd ${resp.status}`;
  let code: string | undefined;
  let requestId: string | undefined = resp.headers.get("X-Request-Id") ?? undefined;
  try {
    const data = await resp.json();
    if (typeof data.detail === "string") detail = data.detail;
    if (typeof data.code === "string") code = data.code;
    if (typeof data.request_id === "string") requestId = data.request_id;
  } catch {
    /* Świadomie: odpowiedź bez poprawnego JSON-a (np. proxy, HTML 502) —
     * zostaje bezpieczny fallback „Błąd <status>". */
  }
  return new ApiError(resp.status, detail, code, requestId);
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  form?: FormData,
  opts?: RequestOpts
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const resp = await fetchOrOffline(
    path,
    {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      credentials: "same-origin",
    },
    opts?.signal
  );
  // 401 przy logowaniu to błędne dane (komunikat z serwera, bez przekierowania);
  // każde inne 401 = sesja wygasła/unieważniona — czyścimy stan i wracamy do
  // logowania z czytelnym komunikatem (obsługuje też wygaśnięcie w innej karcie).
  if (resp.status === 401 && path !== "/api/auth/login") {
    redirectToLogin(SESSION_EXPIRED_MESSAGE);
    throw new ApiError(401, SESSION_EXPIRED_MESSAGE, "UNAUTHORIZED");
  }
  if (!resp.ok) {
    const error = await errorFromResponse(resp);
    if (error.message === "PASSWORD_CHANGE_REQUIRED" && location.pathname !== "/haslo") {
      location.assign("/haslo");
    }
    throw error;
  }
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await resp.json()) as T;
  return (await resp.blob()) as unknown as T;
}

export const api = {
  get: <T>(path: string, opts?: RequestOpts) =>
    request<T>("GET", path, undefined, undefined, opts),
  post: <T>(path: string, body?: unknown, opts?: RequestOpts) =>
    request<T>("POST", path, body, undefined, opts),
  put: <T>(path: string, body?: unknown, opts?: RequestOpts) =>
    request<T>("PUT", path, body, undefined, opts),
  upload: <T>(path: string, file: File, opts?: RequestOpts) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>("POST", path, undefined, form, opts);
  },
};

export interface UploadProgressOpts {
  /** Postęp wysyłania 0..1 (zdarzenia XHR upload.onprogress). */
  onProgress?: (fraction: number) => void;
  /** Anulowanie wysyłki z widoku — przerwane żądanie rzuca ApiError
   * z code="CANCELLED" (patrz isCancel). */
  signal?: AbortSignal;
}

/** Upload pliku z postępem per plik i anulowaniem. fetch() nie raportuje
 * postępu wysyłania, więc ta jedna ścieżka używa XMLHttpRequest —
 * z tym samym modelem błędów (ApiError, klasyfikacja OFFLINE/CANCELLED,
 * powrót do logowania po 401) co wspólny klient API. */
export function uploadFileWithProgress<T>(
  path: string,
  file: File,
  opts?: UploadProgressOpts
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", path);
    const token = getToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    const onAbortSignal = () => xhr.abort();
    opts?.signal?.addEventListener("abort", onAbortSignal);
    const cleanup = () => opts?.signal?.removeEventListener("abort", onAbortSignal);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && opts?.onProgress) opts.onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      cleanup();
      if (xhr.status === 401) {
        redirectToLogin(SESSION_EXPIRED_MESSAGE);
        reject(new ApiError(401, SESSION_EXPIRED_MESSAGE, "UNAUTHORIZED"));
        return;
      }
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        /* Świadomie: odpowiedź bez JSON-a (proxy/HTML) — fallback niżej. */
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data as T);
        return;
      }
      const body = (data ?? {}) as { detail?: string; code?: string; request_id?: string };
      reject(new ApiError(
        xhr.status,
        typeof body.detail === "string" ? body.detail : `Błąd ${xhr.status}`,
        typeof body.code === "string" ? body.code : undefined,
        typeof body.request_id === "string"
          ? body.request_id
          : xhr.getResponseHeader("X-Request-Id") ?? undefined
      ));
    };
    xhr.onerror = () => {
      cleanup();
      reject(new ApiError(0, OFFLINE_MESSAGE, "OFFLINE"));
    };
    xhr.onabort = () => {
      cleanup();
      reject(new ApiError(0, "Żądanie anulowane", "CANCELLED"));
    };
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

// ——— Operacje uwierzytelniania — zawsze przez wspólnego klienta API ———
// (żadnych gołych fetchy: nagłówek Authorization musi trafić do serwera,
// inaczej sesja nie zostanie unieważniona po stronie backendu).

export interface LoginResponse {
  token: string;
  user: SessionUser;
}

export type LoginResult =
  | { kind: "ok"; user: SessionUser }
  | { kind: "mfa"; mfaToken: string };

/** Logowanie. Konto z MFA dostaje po haśle krótkotrwałe wyzwanie —
 * sesja powstaje dopiero po poprawnym kodzie (verifyMfa). */
export async function login(email: string, password: string): Promise<LoginResult> {
  const data = await api.post<LoginResponse & { mfa_required?: boolean; mfa_token?: string }>(
    "/api/auth/login",
    { email, password }
  );
  if (data.mfa_required && data.mfa_token) {
    return { kind: "mfa", mfaToken: data.mfa_token };
  }
  setSession(data.token, data.user);
  return { kind: "ok", user: data.user };
}

/** Drugi krok logowania: kod TOTP z aplikacji albo kod odzyskiwania. */
export async function verifyMfa(mfaToken: string, code: string): Promise<SessionUser> {
  const data = await api.post<LoginResponse>("/api/auth/mfa/verify", {
    mfa_token: mfaToken,
    code,
  });
  setSession(data.token, data.user);
  return data.user;
}

/** Wylogowanie: serwer unieważnia sesję (revoked_at), a lokalny stan jest
 * czyszczony ZAWSZE — także przy utracie połączenia (finally). */
export async function logout(): Promise<void> {
  try {
    await api.post("/api/auth/logout");
  } catch {
    // Brak sieci / wygasła sesja — lokalne wylogowanie i tak następuje.
  } finally {
    clearSession();
    location.assign("/login");
  }
}

/** Zmiana hasła z rotacją tokenu: stary token jest unieważniany na
 * serwerze, odpowiedź niesie nowy — podmieniamy go w bieżącej sesji. */
export async function changePassword(
  currentPassword: string,
  newPassword: string
): Promise<void> {
  const data = await api.post<{ ok: boolean; token: string }>(
    "/api/auth/change-password",
    { current_password: currentPassword, new_password: newPassword }
  );
  const user = getUser();
  if (user) setSession(data.token, { ...user, must_change_password: false });
}

export interface AuthSessionRow {
  id: string;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  user_agent: string | null;
  current: boolean;
}

export const listSessions = () =>
  api.get<{ sessions: AuthSessionRow[] }>("/api/auth/sessions");

export const revokeSession = (sessionId: string) =>
  api.post<{ ok: boolean }>(`/api/auth/sessions/${sessionId}/revoke`);

export const revokeOtherSessions = () =>
  api.post<{ ok: boolean; revoked: number }>("/api/auth/sessions/revoke-others");

// ——— MFA (TOTP), aktywacja konta, reset hasła ————————————————————————————

export interface MfaStatus {
  enabled: boolean;
  pending: boolean;
  setup_required: boolean;
  recovery_codes_left: number;
}

export const getMfaStatus = () => api.get<MfaStatus>("/api/auth/mfa/status");

export const mfaSetup = () =>
  api.post<{ secret: string; otpauth_uri: string }>("/api/auth/mfa/setup");

export const mfaEnable = (code: string) =>
  api.post<{ ok: boolean; recovery_codes: string[] }>("/api/auth/mfa/enable", { code });

export const mfaDisable = (code: string) =>
  api.post<{ ok: boolean }>("/api/auth/mfa/disable", { code });

export const mfaRegenerateRecoveryCodes = (code: string) =>
  api.post<{ ok: boolean; recovery_codes: string[] }>(
    "/api/auth/mfa/recovery-codes/regenerate",
    { code }
  );

export interface SecurityEventRow {
  action: string;
  summary: string;
  created_at: string;
}

export const listSecurityEvents = () =>
  api.get<{ events: SecurityEventRow[] }>("/api/auth/security-events");

export const inspectActivation = (token: string) =>
  api.post<{ email: string; display_name: string }>("/api/auth/activation/inspect", {
    token,
  });

export const activateAccount = (token: string, password: string) =>
  api.post<{ ok: boolean }>("/api/auth/activate", { token, password });

export const requestPasswordReset = (email: string) =>
  api.post<{ ok: boolean; message: string }>("/api/auth/password-reset/request", {
    email,
  });

export const confirmPasswordReset = (token: string, newPassword: string) =>
  api.post<{ ok: boolean }>("/api/auth/password-reset/confirm", {
    token,
    new_password: newPassword,
  });

// --- Autoryzowane pobieranie plików ---------------------------------------
// Chronione pliki (/api/files/{id}) wymagają nagłówka Authorization — zwykły
// <a href> go nie wysyła. Jedyna poprawna ścieżka: pobranie przez klienta
// API do Blob + krótkotrwały URL.createObjectURL (zawsze zwalniany).

export interface FetchedFile {
  blob: Blob;
  /** Nazwa pliku z Content-Disposition backendu (RFC 5987) — jeśli podana. */
  filename: string | null;
}

export async function fetchFile(
  fileId: string,
  opts?: RequestOpts
): Promise<FetchedFile> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetchOrOffline(
    `/api/files/${encodeURIComponent(fileId)}`,
    { headers, credentials: "same-origin" },
    opts?.signal
  );
  if (resp.status === 401) {
    redirectToLogin(SESSION_EXPIRED_MESSAGE);
    throw new ApiError(401, SESSION_EXPIRED_MESSAGE, "UNAUTHORIZED");
  }
  if (!resp.ok) {
    throw await errorFromResponse(resp);
  }
  return {
    blob: await resp.blob(),
    filename: filenameFromDisposition(resp.headers.get("content-disposition")),
  };
}

export async function fetchFileBlob(fileId: string, opts?: RequestOpts): Promise<Blob> {
  return (await fetchFile(fileId, opts)).blob;
}

export async function fetchFileUrl(fileId: string, opts?: RequestOpts): Promise<string> {
  const blob = await fetchFileBlob(fileId, opts);
  return URL.createObjectURL(blob);
}

// --- Raportowanie błędów JS do backendu -------------------------------------
// Wysyłamy WYŁĄCZNIE: typ błędu, etykietę komponentu/miejsca i stos
// zredagowany do nazw własnych plików (patrz errorUtils.redactStack) —
// nigdy komunikatów, URL-i, treści formularzy ani danych. Backend redaguje
// to samo drugi raz i tylko zlicza + loguje (bez trwałej treści).

let reportTimestamps: number[] = [];

export function reportFrontendError(error: unknown, component: string): void {
  try {
    const now = Date.now();
    reportTimestamps = reportTimestamps.filter((t) => now - t < 60_000);
    if (reportTimestamps.length >= 5) return; // limit kliencki 5/min
    reportTimestamps.push(now);
    const payload = {
      type: errorTypeName(error),
      component: component.slice(0, 160),
      stack: redactStack(error instanceof Error ? error.stack : null).join("\n") || null,
    };
    // Celowo surowy fetch (nie request()): raportowanie nie może wpaść w
    // pętlę własnej obsługi błędów ani przekierowań 401.
    void fetch("/api/telemetry/frontend-errors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "same-origin",
      keepalive: true,
    }).catch(() => {
      /* Świadomie zignorowane: raportowanie błędów jest best-effort —
       * jego awaria (offline, 429) nie może generować kolejnych błędów. */
    });
  } catch {
    /* Świadomie zignorowane: jak wyżej — telemetrii nie wolno wywrócić UI. */
  }
}

function clickBlobAnchor(blob: Blob, configure: (a: HTMLAnchorElement) => void) {
  // Klik w <a> tworzony programowo NIE podlega blokadzie popupów
  // (w przeciwieństwie do window.open po await). URL zwalniamy po chwili —
  // musi przeżyć start nawigacji/pobierania.
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.rel = "noopener noreferrer";
  configure(a);
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Zapis blobu na dysk pod wskazaną nazwą (atrybut download). */
export function saveBlobAs(blob: Blob, filename: string) {
  clickBlobAnchor(blob, (a) => {
    a.download = filename;
  });
}

/** Otwarcie blobu w nowej karcie (np. podgląd PDF). */
export function openBlobInNewTab(blob: Blob) {
  clickBlobAnchor(blob, (a) => {
    a.target = "_blank";
  });
}

// Logika dat (localToday, plDate, plDateTime, WEEKDAYS...) mieszka w
// jednym wspólnym module: src/dates.ts — importuj stamtąd.

export const money = (cents: number, currency = "PLN") =>
  `${(cents / 100).toFixed(2).replace(".", ",")} ${currency}`;
