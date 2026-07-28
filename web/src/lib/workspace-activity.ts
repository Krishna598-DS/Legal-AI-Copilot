import type { WorkspaceMode } from "@/lib/routes";

const LAST_KEY = "ldi_last_workspace";
const SEEN_READY_KEY = "ldi_seen_ready_docs";
const DISMISSED_NOTIFS_KEY = "ldi_dismissed_notifs";

export type LastWorkspace = {
  documentId: string;
  filename: string;
  mode: WorkspaceMode;
  at: string; // ISO
};

export function readLastWorkspace(): LastWorkspace | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(LAST_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LastWorkspace;
    if (!parsed?.documentId) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writeLastWorkspace(entry: LastWorkspace) {
  if (typeof window === "undefined") return;
  localStorage.setItem(LAST_KEY, JSON.stringify(entry));
}

export function readSeenReadyIds(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(SEEN_READY_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

export function markReadySeen(ids: string[]) {
  if (typeof window === "undefined") return;
  const next = readSeenReadyIds();
  ids.forEach((id) => next.add(id));
  localStorage.setItem(SEEN_READY_KEY, JSON.stringify([...next]));
}

export function readDismissedNotifs(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(DISMISSED_NOTIFS_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as string[];
    return new Set(Array.isArray(arr) ? arr : []);
  } catch {
    return new Set();
  }
}

export function dismissNotif(id: string) {
  if (typeof window === "undefined") return;
  const next = readDismissedNotifs();
  next.add(id);
  localStorage.setItem(DISMISSED_NOTIFS_KEY, JSON.stringify([...next]));
}

export function relativeTime(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const diff = Date.now() - then;
  const sec = Math.round(diff / 1000);
  if (sec < 60) return "just now";
  const min = Math.round(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.round(hr / 24);
  if (day < 14) return `${day}d ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

export function docStatus(status?: string | null) {
  return (status || "").toUpperCase();
}

export function isProcessing(status?: string | null) {
  const s = docStatus(status);
  return s === "PROCESSING" || s === "UPLOADING";
}

export function isReady(status?: string | null) {
  return docStatus(status) === "READY";
}

export function isFailed(status?: string | null) {
  return docStatus(status) === "FAILED";
}
