// Subskrypcja Web Push — jawny opt-in, wyłączana jednym przyciskiem.
// Wymaga zainstalowanej PWA na iOS (Safari 16.4+) lub przeglądarki z
// obsługą Push API.
import { api } from "./api";

function base64UrlToUint8Array(base64Url: string): Uint8Array {
  const padding = "=".repeat((4 - (base64Url.length % 4)) % 4);
  const base64 = (base64Url + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

export function pushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

export async function enablePush(): Promise<void> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("Nie wyrażono zgody na powiadomienia w przeglądarce.");
  }
  const reg = await navigator.serviceWorker.ready;
  const { key } = await api.get<{ key: string }>("/api/push/public-key");
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: base64UrlToUint8Array(key).buffer as ArrayBuffer,
  });
  const json = sub.toJSON();
  await api.post("/api/push/subscribe", {
    endpoint: sub.endpoint,
    keys: { p256dh: json.keys?.p256dh, auth: json.keys?.auth },
  });
}

export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  await api.post("/api/push/unsubscribe", { endpoint: sub.endpoint });
  await sub.unsubscribe();
}
