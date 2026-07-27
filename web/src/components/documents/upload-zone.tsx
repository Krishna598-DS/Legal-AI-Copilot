"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, X } from "lucide-react";
import { api, apiUrl, errorMessage } from "@/lib/api";
import type { DocumentRow } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "@/design-system";

export type UploadItem = {
  id: string;
  file: File;
  progress: number; // 0-100 upload, then -1 processing
  status: "queued" | "uploading" | "processing" | "ready" | "error";
  error?: string;
  documentId?: string;
};

function uploadWithProgress(
  file: File,
  token: string,
  onProgress: (pct: number) => void
): Promise<DocumentRow> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", apiUrl("/documents/upload"));
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        data = { detail: xhr.responseText };
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        const payload = data as { document?: DocumentRow; id?: string };
        const doc = payload.document;
        if (doc?.id) resolve(doc);
        else reject(new Error("Upload succeeded but no document returned"));
      } else {
        reject(new Error(errorMessage(data, "Upload failed")));
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.onabort = () => reject(new Error("Upload cancelled"));
    const fd = new FormData();
    fd.append("file", file);
    xhr.send(fd);
  });
}

async function waitReady(documentId: string, token: string): Promise<DocumentRow> {
  const started = Date.now();
  while (Date.now() - started < 120000) {
    const doc = await api<DocumentRow>(`/documents/${documentId}`, { token });
    const st = (doc.status || "").toUpperCase();
    if (st === "READY") return doc;
    if (st === "FAILED") {
      throw new Error(doc.processing_error || "Processing failed");
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error("Timed out waiting for document processing");
}

export function UploadZone({
  token,
  onComplete,
  className,
  compact,
}: {
  token: string | null;
  onComplete: (doc: DocumentRow) => void | Promise<void>;
  className?: string;
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [queue, setQueue] = useState<UploadItem[]>([]);
  const dragDepth = useRef(0);

  const processFiles = useCallback(
    async (files: FileList | File[]) => {
      if (!token) {
        toast.error("Sign in to upload documents");
        return;
      }
      const list = Array.from(files).filter((f) => {
        const n = f.name.toLowerCase();
        return n.endsWith(".pdf") || n.endsWith(".txt");
      });
      if (!list.length) {
        toast.error("Only PDF or TXT files up to 10MB are supported");
        return;
      }

      const items: UploadItem[] = list.map((file) => ({
        id: crypto.randomUUID(),
        file,
        progress: 0,
        status: "queued",
      }));
      setQueue((q) => [...items, ...q]);

      for (const item of items) {
        setQueue((q) =>
          q.map((x) => (x.id === item.id ? { ...x, status: "uploading", progress: 0 } : x))
        );
        try {
          const doc = await uploadWithProgress(item.file, token, (pct) => {
            setQueue((q) =>
              q.map((x) => (x.id === item.id ? { ...x, progress: pct } : x))
            );
          });
          setQueue((q) =>
            q.map((x) =>
              x.id === item.id
                ? { ...x, status: "processing", progress: 100, documentId: doc.id }
                : x
            )
          );
          const ready = await waitReady(doc.id, token);
          setQueue((q) =>
            q.map((x) => (x.id === item.id ? { ...x, status: "ready" } : x))
          );
          await onComplete(ready);
          toast.success(`${ready.original_filename} is ready`);
          setTimeout(() => {
            setQueue((q) => q.filter((x) => x.id !== item.id));
          }, 1800);
        } catch (err) {
          const message = err instanceof Error ? err.message : "Upload failed";
          setQueue((q) =>
            q.map((x) =>
              x.id === item.id ? { ...x, status: "error", error: message } : x
            )
          );
          toast.error(message);
        }
      }
    },
    [onComplete, token]
  );

  return (
    <div className={cn("relative", className)}>
      <div
        onDragEnter={(e) => {
          e.preventDefault();
          dragDepth.current += 1;
          setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          dragDepth.current -= 1;
          if (dragDepth.current <= 0) {
            dragDepth.current = 0;
            setDragging(false);
          }
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          dragDepth.current = 0;
          setDragging(false);
          if (e.dataTransfer.files?.length) void processFiles(e.dataTransfer.files);
        }}
        className={cn(
          "rounded-xl border border-dashed transition-colors",
          dragging
            ? "border-primary bg-primary/10"
            : "border-border bg-card/60 hover:border-primary/40",
          compact ? "p-4" : "p-8"
        )}
      >
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <div className="flex size-12 items-center justify-center rounded-full border border-border bg-muted/40 text-muted-foreground">
            <FileUp className="size-5" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">
              Drop PDFs here, or{" "}
              <button
                type="button"
                className="text-primary underline-offset-2 hover:underline"
                onClick={() => inputRef.current?.click()}
              >
                browse
              </button>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              PDF or TXT · up to 10MB · private to your account
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => inputRef.current?.click()}
          >
            Choose files
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) void processFiles(e.target.files);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      {dragging ? (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center rounded-xl border-2 border-primary bg-primary/15 backdrop-blur-[1px]">
          <p className="text-sm font-semibold text-primary">Drop to upload</p>
        </div>
      ) : null}

      {queue.length ? (
        <ul className="mt-3 space-y-2">
          {queue.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-border bg-card px-3 py-2"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="min-w-0 truncate text-sm font-medium">
                  {item.file.name}
                </p>
                <div className="flex items-center gap-2">
                  {item.status === "processing" || item.status === "uploading" ? (
                    <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                  ) : null}
                  {item.status === "error" ? (
                    <button
                      type="button"
                      aria-label="Dismiss"
                      onClick={() =>
                        setQueue((q) => q.filter((x) => x.id !== item.id))
                      }
                    >
                      <X className="size-3.5 text-muted-foreground" />
                    </button>
                  ) : null}
                </div>
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {item.status === "uploading" && `Uploading… ${item.progress}%`}
                {item.status === "processing" && "Indexing for cited answers…"}
                {item.status === "ready" && "Ready"}
                {item.status === "error" && item.error}
                {item.status === "queued" && "Queued"}
              </p>
              {(item.status === "uploading" || item.status === "processing") && (
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full bg-primary transition-all",
                      item.status === "processing" && "w-full animate-pulse"
                    )}
                    style={
                      item.status === "uploading"
                        ? { width: `${item.progress}%` }
                        : undefined
                    }
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
