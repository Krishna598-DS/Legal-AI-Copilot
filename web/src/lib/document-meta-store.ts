/**
 * Client-side document library metadata (folders + tags).
 * Server sync is deferred — keyed by user email so accounts don't collide.
 */

export type LibraryFolder = {
  id: string;
  name: string;
  createdAt: string;
};

export type DocumentMetaStore = {
  folders: LibraryFolder[];
  /** documentId → folderId | null */
  docFolder: Record<string, string | null>;
  /** documentId → tag labels */
  docTags: Record<string, string[]>;
};

const PREFIX = "ldi_doc_meta_v1:";

function keyFor(userKey: string) {
  return `${PREFIX}${userKey || "anon"}`;
}

function emptyStore(): DocumentMetaStore {
  return { folders: [], docFolder: {}, docTags: {} };
}

export function readDocumentMeta(userKey: string): DocumentMetaStore {
  if (typeof window === "undefined") return emptyStore();
  try {
    const raw = localStorage.getItem(keyFor(userKey));
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as DocumentMetaStore;
    return {
      folders: Array.isArray(parsed.folders) ? parsed.folders : [],
      docFolder: parsed.docFolder && typeof parsed.docFolder === "object" ? parsed.docFolder : {},
      docTags: parsed.docTags && typeof parsed.docTags === "object" ? parsed.docTags : {},
    };
  } catch {
    return emptyStore();
  }
}

export function writeDocumentMeta(userKey: string, store: DocumentMetaStore) {
  if (typeof window === "undefined") return;
  localStorage.setItem(keyFor(userKey), JSON.stringify(store));
}

export function createFolder(userKey: string, name: string): DocumentMetaStore {
  const store = readDocumentMeta(userKey);
  const trimmed = name.trim();
  if (!trimmed) return store;
  if (store.folders.some((f) => f.name.toLowerCase() === trimmed.toLowerCase())) {
    return store;
  }
  store.folders.push({
    id: crypto.randomUUID(),
    name: trimmed,
    createdAt: new Date().toISOString(),
  });
  writeDocumentMeta(userKey, store);
  return store;
}

export function renameFolder(
  userKey: string,
  folderId: string,
  name: string
): DocumentMetaStore {
  const store = readDocumentMeta(userKey);
  const folder = store.folders.find((f) => f.id === folderId);
  if (folder) folder.name = name.trim() || folder.name;
  writeDocumentMeta(userKey, store);
  return store;
}

export function deleteFolder(userKey: string, folderId: string): DocumentMetaStore {
  const store = readDocumentMeta(userKey);
  store.folders = store.folders.filter((f) => f.id !== folderId);
  for (const [docId, fid] of Object.entries(store.docFolder)) {
    if (fid === folderId) store.docFolder[docId] = null;
  }
  writeDocumentMeta(userKey, store);
  return store;
}

export function moveDocToFolder(
  userKey: string,
  documentId: string,
  folderId: string | null
): DocumentMetaStore {
  const store = readDocumentMeta(userKey);
  store.docFolder[documentId] = folderId;
  writeDocumentMeta(userKey, store);
  return store;
}

export function setDocTags(
  userKey: string,
  documentId: string,
  tags: string[]
): DocumentMetaStore {
  const store = readDocumentMeta(userKey);
  const cleaned = [
    ...new Set(
      tags
        .map((t) => t.trim())
        .filter(Boolean)
        .map((t) => t.slice(0, 32))
    ),
  ].slice(0, 12);
  store.docTags[documentId] = cleaned;
  writeDocumentMeta(userKey, store);
  return store;
}

export function allTags(store: DocumentMetaStore): string[] {
  const set = new Set<string>();
  Object.values(store.docTags).forEach((tags) => tags.forEach((t) => set.add(t)));
  return [...set].sort((a, b) => a.localeCompare(b));
}

export type LibraryViewMode = "grid" | "list";
export type StatusFilter = "all" | "ready" | "processing" | "failed";
export type SortKey = "name" | "date" | "size" | "status";

export type LibraryPrefs = {
  view: LibraryViewMode;
  sort: SortKey;
  sortDir: "asc" | "desc";
  pageSize: number;
};

const PREFS_KEY = "ldi_library_prefs_v1";

export function readLibraryPrefs(): LibraryPrefs {
  if (typeof window === "undefined") {
    return { view: "grid", sort: "date", sortDir: "desc", pageSize: 24 };
  }
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return { view: "grid", sort: "date", sortDir: "desc", pageSize: 24 };
    const p = JSON.parse(raw) as Partial<LibraryPrefs>;
    return {
      view: p.view === "list" ? "list" : "grid",
      sort:
        p.sort === "name" || p.sort === "size" || p.sort === "status" ? p.sort : "date",
      sortDir: p.sortDir === "asc" ? "asc" : "desc",
      pageSize: [12, 24, 48].includes(p.pageSize || 0) ? (p.pageSize as number) : 24,
    };
  } catch {
    return { view: "grid", sort: "date", sortDir: "desc", pageSize: 24 };
  }
}

export function writeLibraryPrefs(prefs: LibraryPrefs) {
  if (typeof window === "undefined") return;
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}
