/**
 * Client-side bookmarks + notes for the PDF reader.
 * Keyed by document id. Server sync deferred.
 */

export type ReaderBookmark = {
  id: string;
  page: number;
  label: string;
  createdAt: string;
};

export type ReaderNote = {
  id: string;
  page: number;
  text: string;
  quote?: string;
  createdAt: string;
  updatedAt: string;
};

export type ReaderAnnotations = {
  bookmarks: ReaderBookmark[];
  notes: ReaderNote[];
};

const PREFIX = "ldi_reader_v1:";

function empty(): ReaderAnnotations {
  return { bookmarks: [], notes: [] };
}

export function readAnnotations(documentId: string): ReaderAnnotations {
  if (typeof window === "undefined" || !documentId) return empty();
  try {
    const raw = localStorage.getItem(PREFIX + documentId);
    if (!raw) return empty();
    const parsed = JSON.parse(raw) as ReaderAnnotations;
    return {
      bookmarks: Array.isArray(parsed.bookmarks) ? parsed.bookmarks : [],
      notes: Array.isArray(parsed.notes) ? parsed.notes : [],
    };
  } catch {
    return empty();
  }
}

export function writeAnnotations(documentId: string, data: ReaderAnnotations) {
  if (typeof window === "undefined" || !documentId) return;
  localStorage.setItem(PREFIX + documentId, JSON.stringify(data));
}

export function addBookmark(
  documentId: string,
  page: number,
  label?: string
): ReaderAnnotations {
  const data = readAnnotations(documentId);
  if (data.bookmarks.some((b) => b.page === page)) return data;
  data.bookmarks.push({
    id: crypto.randomUUID(),
    page,
    label: label || `Page ${page}`,
    createdAt: new Date().toISOString(),
  });
  data.bookmarks.sort((a, b) => a.page - b.page);
  writeAnnotations(documentId, data);
  return data;
}

export function removeBookmark(documentId: string, id: string): ReaderAnnotations {
  const data = readAnnotations(documentId);
  data.bookmarks = data.bookmarks.filter((b) => b.id !== id);
  writeAnnotations(documentId, data);
  return data;
}

export function addNote(
  documentId: string,
  page: number,
  text: string,
  quote?: string
): ReaderAnnotations {
  const data = readAnnotations(documentId);
  const now = new Date().toISOString();
  data.notes.unshift({
    id: crypto.randomUUID(),
    page,
    text: text.trim(),
    quote: quote?.trim() || undefined,
    createdAt: now,
    updatedAt: now,
  });
  writeAnnotations(documentId, data);
  return data;
}

export function updateNote(
  documentId: string,
  id: string,
  text: string
): ReaderAnnotations {
  const data = readAnnotations(documentId);
  const note = data.notes.find((n) => n.id === id);
  if (note) {
    note.text = text.trim();
    note.updatedAt = new Date().toISOString();
  }
  writeAnnotations(documentId, data);
  return data;
}

export function removeNote(documentId: string, id: string): ReaderAnnotations {
  const data = readAnnotations(documentId);
  data.notes = data.notes.filter((n) => n.id !== id);
  writeAnnotations(documentId, data);
  return data;
}
