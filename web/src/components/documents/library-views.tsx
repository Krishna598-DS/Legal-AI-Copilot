"use client";

import { Skeleton } from "@/components/ui/skeleton";
import type { DocumentRow as Doc } from "@/lib/types";
import type { DocActions } from "./doc-actions";
import { DocumentCard, DocumentRow as DocRow } from "./document-item";

export function LibraryGrid({
  docs,
  token,
  actions,
}: {
  docs: Doc[];
  token: string | null;
  actions: DocActions;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {docs.map((doc, i) => (
        <DocumentCard
          key={doc.id}
          doc={doc}
          token={token}
          actions={actions}
          index={i}
        />
      ))}
    </div>
  );
}

export function LibraryList({
  docs,
  token,
  actions,
}: {
  docs: Doc[];
  token: string | null;
  actions: DocActions;
}) {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <div className="hidden grid-cols-[48px_minmax(0,1.4fr)_100px_88px_100px_120px_40px] gap-3 border-b border-border px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground md:grid">
        <span />
        <span>Name</span>
        <span>Status</span>
        <span>Size</span>
        <span>Pages</span>
        <span>Added</span>
        <span />
      </div>
      {docs.map((doc) => (
        <DocRow key={doc.id} doc={doc} token={token} actions={actions} />
      ))}
    </div>
  );
}

export function LibraryGridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="rounded-xl border border-border bg-card p-2.5">
          <Skeleton className="aspect-[3/4] w-full rounded-md" />
          <Skeleton className="mt-3 h-4 w-3/4" />
          <Skeleton className="mt-2 h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

export function LibraryListSkeleton() {
  return (
    <div className="space-y-2 rounded-xl border border-border bg-card p-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="size-12 rounded-md" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-3 w-1/4" />
          </div>
        </div>
      ))}
    </div>
  );
}
