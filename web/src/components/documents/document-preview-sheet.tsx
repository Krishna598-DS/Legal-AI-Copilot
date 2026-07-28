"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Download,
  ExternalLink,
  FileText,
  Loader2,
} from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/design-system";
import { apiUrl } from "@/lib/api";
import type { DocumentRow } from "@/lib/types";
import { formatBytes } from "@/lib/use-document-library";
import { relativeTime } from "@/lib/workspace-activity";
import { DocumentThumbnail } from "./document-thumbnail";

export function DocumentPreviewSheet({
  doc,
  open,
  onOpenChange,
  token,
  tags,
  folderName,
  onOpenWorkspace,
  onOpenReader,
  onDownload,
}: {
  doc: DocumentRow | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token: string | null;
  tags: string[];
  folderName?: string | null;
  onOpenWorkspace: () => void;
  onOpenReader?: () => void;
  onDownload: () => void;
}) {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const isPdf = useMemo(
    () => (doc?.original_filename || "").toLowerCase().endsWith(".pdf"),
    [doc?.original_filename]
  );

  useEffect(() => {
    if (!open || !doc || !token) {
      setPreviewUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    setLoadingPreview(true);
    (async () => {
      try {
        const res = await fetch(apiUrl(`/documents/${doc.id}/download`), {
          headers: { Authorization: `Bearer ${token}` },
          redirect: "follow",
        });
        if (!res.ok) throw new Error("download failed");
        // If redirected to signed URL, res.url may be external; blob still works for same-origin
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      } catch {
        if (!cancelled) setPreviewUrl(null);
      } finally {
        if (!cancelled) setLoadingPreview(false);
      }
    })();
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [doc, open, token]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle className="pr-6 leading-snug">
            {doc?.original_filename || "Document"}
          </SheetTitle>
          <SheetDescription>Preview and metadata</SheetDescription>
        </SheetHeader>

        {doc ? (
          <div className="mt-6 space-y-5 px-1">
            <div className="mx-auto w-40">
              <DocumentThumbnail
                documentId={doc.id}
                filename={doc.original_filename}
                status={doc.status}
                token={token}
              />
            </div>

            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="primary" onClick={onOpenWorkspace}>
                <ExternalLink className="size-3.5" />
                Open workspace
              </Button>
              {onOpenReader ? (
                <Button size="sm" variant="secondary" onClick={onOpenReader}>
                  <FileText className="size-3.5" />
                  Read
                </Button>
              ) : null}
              <Button size="sm" variant="outline" onClick={onDownload}>
                <Download className="size-3.5" />
                Download
              </Button>
            </div>

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-muted-foreground">Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={doc.status} />
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Added</dt>
                <dd className="mt-1">{relativeTime(doc.created_at) || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Size</dt>
                <dd className="mt-1">{formatBytes(doc.file_size_bytes)}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Pages</dt>
                <dd className="mt-1">{doc.page_count || "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Chunks</dt>
                <dd className="mt-1">{doc.num_chunks ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Folder</dt>
                <dd className="mt-1">{folderName || "Unfiled"}</dd>
              </div>
            </dl>

            {tags.length ? (
              <div>
                <p className="text-xs text-muted-foreground">Tags</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-md border border-border bg-muted/50 px-2 py-0.5 text-xs"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}

            {doc.processing_error ? (
              <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                {doc.processing_error}
              </p>
            ) : null}

            <div>
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                File preview
              </p>
              <div className="min-h-[280px] overflow-hidden rounded-lg border border-border bg-muted/30">
                {loadingPreview ? (
                  <div className="flex h-[280px] items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    Loading…
                  </div>
                ) : previewUrl && isPdf ? (
                  <iframe
                    title="PDF preview"
                    src={previewUrl}
                    className="h-[420px] w-full"
                  />
                ) : previewUrl && !isPdf ? (
                  <iframe
                    title="Text preview"
                    src={previewUrl}
                    className="h-[320px] w-full bg-background"
                  />
                ) : (
                  <div className="flex h-[200px] flex-col items-center justify-center gap-2 text-muted-foreground">
                    <FileText className="size-8 opacity-50" />
                    <p className="text-xs">Preview unavailable — download to view</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
