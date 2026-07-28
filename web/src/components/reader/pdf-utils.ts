"use client";

import { useMemo } from "react";
import { pdfjs } from "react-pdf";

/** Configure PDF.js worker once (CDN — reliable for static export). */
let configured = false;

export function ensurePdfWorker() {
  if (configured || typeof window === "undefined") return;
  pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  configured = true;
}

export function usePdfFileUrl(token: string | null, documentId: string | null) {
  return useMemo(() => {
    if (!token || !documentId) return null;
    // Auth via query is not supported — caller must fetch blob.
    return { token, documentId };
  }, [token, documentId]);
}

export async function fetchPdfBlob(
  token: string,
  documentId: string
): Promise<Blob> {
  const { apiUrl } = await import("@/lib/api");
  const res = await fetch(apiUrl(`/documents/${documentId}/download`), {
    headers: { Authorization: `Bearer ${token}` },
    redirect: "follow",
  });
  if (!res.ok) throw new Error("Failed to load PDF");
  return res.blob();
}
