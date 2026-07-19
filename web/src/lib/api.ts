const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export function apiUrl(path: string) {
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export function errorMessage(payload: unknown, fallback = "Request failed") {
  if (!payload || typeof payload !== "object") return fallback;
  const p = payload as Record<string, unknown>;
  const err = p.error as { message?: string } | undefined;
  if (err?.message) return err.message;
  const detail = p.detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) =>
        typeof d === "object" && d && "msg" in d
          ? String((d as { msg: string }).msg)
          : JSON.stringify(d)
      )
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    const d = detail as { message?: string; code?: string };
    return d.message || d.code || fallback;
  }
  if (typeof detail === "string") return detail;
  return fallback;
}

export async function api<T = unknown>(
  path: string,
  opts: RequestInit & { json?: unknown; token?: string | null } = {}
): Promise<T> {
  const headers = new Headers(opts.headers || {});
  if (opts.token) headers.set("Authorization", `Bearer ${opts.token}`);
  let body = opts.body;
  if (opts.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(opts.json);
  }
  const { json: _json, token: _token, ...rest } = opts;
  void _json;
  void _token;
  const res = await fetch(apiUrl(path), { ...rest, headers, body });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!res.ok) throw new Error(errorMessage(data, res.statusText));
  return data as T;
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("ldi_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem("ldi_token", token);
  else localStorage.removeItem("ldi_token");
}
