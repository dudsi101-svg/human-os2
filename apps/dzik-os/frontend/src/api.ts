// Warstwa komunikacji z backendem. Frontend NIE podejmuje decyzji
// bezpieczeństwa — każde żądanie jest autoryzowane po stronie Core/backendu
// (kontrakt ADR-ARCH-003: UI -> Request -> Core -> Receipt -> UI).

export interface SessionUser {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  must_change_password?: boolean;
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
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  form?: FormData
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const resp = await fetch(path, {
    method,
    headers,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    credentials: "same-origin",
  });
  // 401 przy logowaniu to błędne dane (komunikat z serwera, bez przekierowania);
  // każde inne 401 = sesja wygasła/unieważniona — czyścimy stan i wracamy do
  // logowania (obsługuje też wygaśnięcie sesji w innej karcie).
  if (resp.status === 401 && path !== "/api/auth/login") {
    clearSession();
    if (!location.pathname.startsWith("/login")) location.assign("/login");
    throw new ApiError(401, "Sesja wygasła");
  }
  if (!resp.ok) {
    let detail = `Błąd ${resp.status}`;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* ignore */
    }
    if (detail === "PASSWORD_CHANGE_REQUIRED" && location.pathname !== "/haslo") {
      location.assign("/haslo");
    }
    throw new ApiError(resp.status, detail);
  }
  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await resp.json()) as T;
  return (await resp.blob()) as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  upload: <T>(path: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>("POST", path, undefined, form);
  },
};

// ——— Operacje uwierzytelniania — zawsze przez wspólnego klienta API ———
// (żadnych gołych fetchy: nagłówek Authorization musi trafić do serwera,
// inaczej sesja nie zostanie unieważniona po stronie backendu).

export interface LoginResponse {
  token: string;
  user: SessionUser;
}

export async function login(email: string, password: string): Promise<SessionUser> {
  const data = await api.post<LoginResponse>("/api/auth/login", { email, password });
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

export async function fetchFileBlob(fileId: string): Promise<Blob> {
  return api.get<Blob>(`/api/files/${fileId}`);
}

export async function fetchFileUrl(fileId: string): Promise<string> {
  const blob = await fetchFileBlob(fileId);
  return URL.createObjectURL(blob);
}

// Logika dat (localToday, plDate, plDateTime, WEEKDAYS...) mieszka w
// jednym wspólnym module: src/dates.ts — importuj stamtąd.

export const money = (cents: number, currency = "PLN") =>
  `${(cents / 100).toFixed(2).replace(".", ",")} ${currency}`;
