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
  if (resp.status === 401) {
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

// --- Autoryzowane pobieranie plików ---------------------------------------
// Chronione pliki (/api/files/{id}) wymagają nagłówka Authorization — zwykły
// <a href> go nie wysyła. Jedyna poprawna ścieżka: pobranie przez klienta
// API do Blob + krótkotrwały URL.createObjectURL (zawsze zwalniany).

export interface FetchedFile {
  blob: Blob;
  /** Nazwa pliku z Content-Disposition backendu (RFC 5987) — jeśli podana. */
  filename: string | null;
}

function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1].trim());
    } catch {
      /* uszkodzone kodowanie — spróbuj zwykłego filename */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : null;
}

export async function fetchFile(fileId: string): Promise<FetchedFile> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const resp = await fetch(`/api/files/${encodeURIComponent(fileId)}`, {
    headers,
    credentials: "same-origin",
  });
  if (resp.status === 401) {
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
    throw new ApiError(resp.status, detail);
  }
  return {
    blob: await resp.blob(),
    filename: filenameFromDisposition(resp.headers.get("content-disposition")),
  };
}

export async function fetchFileBlob(fileId: string): Promise<Blob> {
  return (await fetchFile(fileId)).blob;
}

export async function fetchFileUrl(fileId: string): Promise<string> {
  const blob = await fetchFileBlob(fileId);
  return URL.createObjectURL(blob);
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

export const todayIso = () => new Date().toISOString().slice(0, 10);

export const money = (cents: number, currency = "PLN") =>
  `${(cents / 100).toFixed(2).replace(".", ",")} ${currency}`;

export const plDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString("pl-PL", { day: "numeric", month: "long", year: "numeric" }) : "—";

export const plDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("pl-PL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";

export const WEEKDAYS = ["pon", "wt", "śr", "czw", "pt", "sob", "niedz"];
