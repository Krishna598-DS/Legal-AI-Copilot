"use client";

import type { DocumentRow } from "@/lib/types";
import type { LibraryFolder } from "@/lib/document-meta-store";

export type DocActions = {
  onOpen: (doc: DocumentRow) => void;
  onRead: (doc: DocumentRow) => void;
  onPreview: (doc: DocumentRow) => void;
  onRename: (doc: DocumentRow) => void;
  onDownload: (doc: DocumentRow) => void;
  onDelete: (doc: DocumentRow) => void;
  onMove: (doc: DocumentRow, folderId: string | null) => void;
  onEditTags: (doc: DocumentRow) => void;
  folders: LibraryFolder[];
  tagsFor: (docId: string) => string[];
};
