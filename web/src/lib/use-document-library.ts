"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { DocumentRow } from "@/lib/types";
import {
  allTags,
  createFolder,
  deleteFolder,
  moveDocToFolder,
  readDocumentMeta,
  readLibraryPrefs,
  renameFolder,
  setDocTags,
  writeLibraryPrefs,
  type DocumentMetaStore,
  type LibraryPrefs,
  type SortKey,
  type StatusFilter,
} from "@/lib/document-meta-store";
import { isFailed, isProcessing, isReady } from "@/lib/workspace-activity";

export type FolderScope = "all" | "unfiled" | string; // string = folder id

function matchesStatus(d: DocumentRow, filter: StatusFilter) {
  if (filter === "all") return true;
  if (filter === "ready") return isReady(d.status);
  if (filter === "failed") return isFailed(d.status);
  return isProcessing(d.status);
}

function compareDocs(
  a: DocumentRow,
  b: DocumentRow,
  sort: SortKey,
  dir: "asc" | "desc"
) {
  const mul = dir === "asc" ? 1 : -1;
  switch (sort) {
    case "name":
      return (
        mul *
        (a.original_filename || "").localeCompare(b.original_filename || "", undefined, {
          sensitivity: "base",
        })
      );
    case "size":
      return mul * ((a.file_size_bytes || 0) - (b.file_size_bytes || 0));
    case "status":
      return mul * (a.status || "").localeCompare(b.status || "");
    case "date":
    default: {
      const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
      const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
      return mul * (ta - tb);
    }
  }
}

export function useDocumentLibrary(docs: DocumentRow[], userKey: string) {
  const [meta, setMeta] = useState<DocumentMetaStore>(() =>
    typeof window === "undefined" ? { folders: [], docFolder: {}, docTags: {} } : readDocumentMeta(userKey)
  );
  const [prefs, setPrefs] = useState<LibraryPrefs>(() =>
    typeof window === "undefined"
      ? { view: "grid", sort: "date", sortDir: "desc", pageSize: 24 }
      : readLibraryPrefs()
  );
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [tagFilter, setTagFilter] = useState<string | null>(null);
  const [folderScope, setFolderScope] = useState<FolderScope>("all");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setMeta(readDocumentMeta(userKey));
  }, [userKey]);

  useEffect(() => {
    writeLibraryPrefs(prefs);
  }, [prefs]);

  useEffect(() => {
    setPage(1);
  }, [query, statusFilter, tagFilter, folderScope, prefs.sort, prefs.sortDir, prefs.pageSize]);

  const tagsCatalog = useMemo(() => allTags(meta), [meta]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return docs
      .filter((d) => {
        if (!matchesStatus(d, statusFilter)) return false;
        if (folderScope === "unfiled") {
          if (meta.docFolder[d.id]) return false;
        } else if (folderScope !== "all") {
          if (meta.docFolder[d.id] !== folderScope) return false;
        }
        if (tagFilter) {
          const tags = meta.docTags[d.id] || [];
          if (!tags.includes(tagFilter)) return false;
        }
        if (q) {
          const name = (d.original_filename || "").toLowerCase();
          const tags = (meta.docTags[d.id] || []).join(" ").toLowerCase();
          if (!name.includes(q) && !tags.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => compareDocs(a, b, prefs.sort, prefs.sortDir));
  }, [docs, folderScope, meta, prefs.sort, prefs.sortDir, query, statusFilter, tagFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / prefs.pageSize));
  const safePage = Math.min(page, totalPages);
  const pageItems = useMemo(() => {
    const start = (safePage - 1) * prefs.pageSize;
    return filtered.slice(start, start + prefs.pageSize);
  }, [filtered, prefs.pageSize, safePage]);

  const refreshMeta = useCallback(() => {
    setMeta(readDocumentMeta(userKey));
  }, [userKey]);

  return {
    meta,
    prefs,
    setPrefs,
    query,
    setQuery,
    statusFilter,
    setStatusFilter,
    tagFilter,
    setTagFilter,
    folderScope,
    setFolderScope,
    page: safePage,
    setPage,
    totalPages,
    filtered,
    pageItems,
    tagsCatalog,
    createFolder: (name: string) => {
      setMeta(createFolder(userKey, name));
    },
    renameFolder: (id: string, name: string) => {
      setMeta(renameFolder(userKey, id, name));
    },
    deleteFolder: (id: string) => {
      setMeta(deleteFolder(userKey, id));
      if (folderScope === id) setFolderScope("all");
    },
    moveDoc: (documentId: string, folderId: string | null) => {
      setMeta(moveDocToFolder(userKey, documentId, folderId));
    },
    setTags: (documentId: string, tags: string[]) => {
      setMeta(setDocTags(userKey, documentId, tags));
    },
    refreshMeta,
  };
}

export function formatBytes(n?: number | null) {
  if (n == null || n <= 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
