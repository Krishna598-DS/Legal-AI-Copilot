/**
 * Device-local settings preferences (notifications, API key labels, devices).
 * Server sync for these arrives with the session/auth upgrade.
 */

export type NotificationPrefs = {
  documentReady: boolean;
  documentFailed: boolean;
  emailVerifyReminders: boolean;
  productTips: boolean;
};

export type LocalApiKey = {
  id: string;
  name: string;
  prefix: string;
  /** Full secret shown once at creation; afterwards only prefix is kept. */
  secret?: string;
  createdAt: string;
  lastUsedAt?: string;
};

export type ConnectedDevice = {
  id: string;
  label: string;
  userAgent: string;
  lastSeenAt: string;
  current: boolean;
};

const NOTIF_KEY = "ldi_settings_notif_v1";
const KEYS_KEY = "ldi_settings_apikeys_v1:";
const DEVICES_KEY = "ldi_settings_devices_v1:";

export const DEFAULT_NOTIFICATIONS: NotificationPrefs = {
  documentReady: true,
  documentFailed: true,
  emailVerifyReminders: true,
  productTips: false,
};

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function readNotificationPrefs(): NotificationPrefs {
  return { ...DEFAULT_NOTIFICATIONS, ...readJson(NOTIF_KEY, {}) };
}

export function writeNotificationPrefs(prefs: NotificationPrefs) {
  if (typeof window === "undefined") return;
  localStorage.setItem(NOTIF_KEY, JSON.stringify(prefs));
}

export function readApiKeys(userId: string): LocalApiKey[] {
  if (!userId) return [];
  return readJson<LocalApiKey[]>(KEYS_KEY + userId, []).map((k) => ({
    ...k,
    secret: undefined,
  }));
}

export function createApiKey(
  userId: string,
  name: string
): { list: LocalApiKey[]; created: LocalApiKey } {
  const list = readJson<LocalApiKey[]>(KEYS_KEY + userId, []);
  const raw = crypto.getRandomValues(new Uint8Array(24));
  const secret = `ldi_${Array.from(raw, (b) => b.toString(16).padStart(2, "0")).join("")}`;
  const created: LocalApiKey = {
    id: crypto.randomUUID(),
    name: name.trim() || "Personal key",
    prefix: `${secret.slice(0, 10)}…`,
    secret,
    createdAt: new Date().toISOString(),
  };
  const next = [{ ...created, secret: undefined }, ...list];
  localStorage.setItem(KEYS_KEY + userId, JSON.stringify(next));
  return { list: next, created };
}

export function revokeApiKey(userId: string, id: string): LocalApiKey[] {
  const next = readJson<LocalApiKey[]>(KEYS_KEY + userId, []).filter((k) => k.id !== id);
  localStorage.setItem(KEYS_KEY + userId, JSON.stringify(next));
  return next;
}

function deviceLabel(ua: string): string {
  const browser = /Edg\//.test(ua)
    ? "Edge"
    : /Chrome\//.test(ua)
      ? "Chrome"
      : /Firefox\//.test(ua)
        ? "Firefox"
        : /Safari\//.test(ua)
          ? "Safari"
          : "Browser";
  const os = /Windows/.test(ua)
    ? "Windows"
    : /Mac OS X/.test(ua)
      ? "macOS"
      : /Android/.test(ua)
        ? "Android"
        : /iPhone|iPad/.test(ua)
          ? "iOS"
          : /Linux/.test(ua)
            ? "Linux"
            : "Unknown OS";
  return `${browser} on ${os}`;
}

export function touchCurrentDevice(userId: string): ConnectedDevice[] {
  if (typeof window === "undefined" || !userId) return [];
  const ua = navigator.userAgent;
  const fingerprint = `${ua.slice(0, 80)}|${navigator.language}|${screen.width}x${screen.height}`;
  let id = "dev_unknown";
  try {
    id = `dev_${btoa(fingerprint).replace(/[^a-zA-Z0-9]/g, "").slice(0, 18)}`;
  } catch {
    id = `dev_${fingerprint.length}`;
  }
  const list = readJson<ConnectedDevice[]>(DEVICES_KEY + userId, []);
  const now = new Date().toISOString();
  const existing = list.find((d) => d.id === id);
  let next: ConnectedDevice[];
  if (existing) {
    next = list.map((d) =>
      d.id === id
        ? { ...d, lastSeenAt: now, current: true, label: deviceLabel(ua), userAgent: ua }
        : { ...d, current: false }
    );
  } else {
    next = [
      {
        id,
        label: deviceLabel(ua),
        userAgent: ua,
        lastSeenAt: now,
        current: true,
      },
      ...list.map((d) => ({ ...d, current: false })),
    ].slice(0, 12);
  }
  localStorage.setItem(DEVICES_KEY + userId, JSON.stringify(next));
  return next;
}

export function readDevices(userId: string): ConnectedDevice[] {
  return readJson(DEVICES_KEY + userId, []);
}

export function removeDevice(userId: string, id: string): ConnectedDevice[] {
  const next = readDevices(userId).filter((d) => d.id !== id);
  localStorage.setItem(DEVICES_KEY + userId, JSON.stringify(next));
  return next;
}

/** Decode JWT payload without verifying (UI display only). */
export function peekJwtClaims(token: string | null): {
  sub?: string;
  exp?: number;
  iat?: number;
} | null {
  if (!token) return null;
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as { sub?: string; exp?: number; iat?: number };
  } catch {
    return null;
  }
}
