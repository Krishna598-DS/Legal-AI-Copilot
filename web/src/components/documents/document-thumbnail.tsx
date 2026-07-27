"use client";

import { useEffect, useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { isProcessing } from "@/lib/workspace-activity";
import { cn } from "@/lib/utils";

export function DocumentThumbnail({
  documentId,
  filename,
  status,
  token,
  className,
}: {
  documentId: string;
  filename?: string;
  status?: string;
  token: string | null;
  className?: string;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const processing = isProcessing(status);

  useEffect(() => {
    if (!token || !documentId) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    setFailed(false);
    setSrc(null);

    (async () => {
      try {
        const res = await fetch(apiUrl(`/documents/${documentId}/thumbnail`), {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("thumb failed");
        const blob = await res.blob();
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [documentId, token]);

  return (
    <div
      className={cn(
        "relative flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-md border border-border bg-muted/40",
        className
      )}
    >
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          className="h-full w-full object-cover object-top"
        />
      ) : (
        <div className="flex flex-col items-center gap-2 px-3 text-center text-muted-foreground">
          <FileText className="size-8 opacity-60" />
          <span className="line-clamp-3 text-[10px] leading-tight">
            {filename || "Document"}
          </span>
        </div>
      )}
      {processing ? (
        <div className="absolute inset-0 flex items-center justify-center bg-background/55 backdrop-blur-[1px]">
          <Loader2 className="size-5 animate-spin text-primary" />
        </div>
      ) : null}
    </div>
  );
}
