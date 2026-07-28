"use client";

import { motion } from "framer-motion";
import { StatusBadge } from "@/design-system";
import type { DocumentRow } from "@/lib/types";
import { relativeTime } from "@/lib/workspace-activity";
import { formatBytes } from "@/lib/use-document-library";
import { DocumentThumbnail } from "./document-thumbnail";
import { DocumentContextMenu, DocumentMoreMenu } from "./document-menus";
import type { DocActions } from "./doc-actions";
import { cn } from "@/lib/utils";

export function DocumentCard({
  doc,
  token,
  actions,
  index = 0,
}: {
  doc: DocumentRow;
  token: string | null;
  actions: DocActions;
  index?: number;
}) {
  const tags = actions.tagsFor(doc.id);
  return (
    <DocumentContextMenu doc={doc} actions={actions}>
      <motion.div
        layout
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18, delay: Math.min(index * 0.03, 0.24) }}
        className={cn(
          "group relative flex cursor-pointer flex-col rounded-xl border border-border bg-card p-2.5 shadow-sm transition-colors hover:border-primary/40"
        )}
        onDoubleClick={() => actions.onOpen(doc)}
        onClick={() => actions.onPreview(doc)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter") actions.onOpen(doc);
        }}
      >
        <DocumentThumbnail
          documentId={doc.id}
          filename={doc.original_filename}
          status={doc.status}
          token={token}
        />
        <div className="mt-2 flex items-start justify-between gap-1">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">
              {doc.original_filename}
            </p>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <StatusBadge status={doc.status} />
              <span className="text-[11px] text-muted-foreground">
                {relativeTime(doc.created_at) || "—"}
              </span>
            </div>
            {tags.length ? (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {tags.slice(0, 3).map((t) => (
                  <span
                    key={t}
                    className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                  >
                    {t}
                  </span>
                ))}
              </div>
            ) : null}
            <p className="mt-1 text-[11px] text-muted-foreground">
              {formatBytes(doc.file_size_bytes)}
              {doc.page_count ? ` · ${doc.page_count}p` : ""}
            </p>
          </div>
          <DocumentMoreMenu doc={doc} actions={actions} />
        </div>
      </motion.div>
    </DocumentContextMenu>
  );
}

export function DocumentRow({
  doc,
  token,
  actions,
}: {
  doc: DocumentRow;
  token: string | null;
  actions: DocActions;
}) {
  const tags = actions.tagsFor(doc.id);
  return (
    <DocumentContextMenu doc={doc} actions={actions}>
      <div
        className="group grid cursor-pointer grid-cols-[40px_1fr_auto] items-center gap-3 border-b border-border px-3 py-2.5 transition-colors hover:bg-muted/50 md:grid-cols-[48px_minmax(0,1.4fr)_100px_88px_100px_120px_40px]"
        onDoubleClick={() => actions.onOpen(doc)}
        onClick={() => actions.onPreview(doc)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter") actions.onOpen(doc);
        }}
      >
        <DocumentThumbnail
          documentId={doc.id}
          filename={doc.original_filename}
          status={doc.status}
          token={token}
          className="aspect-square w-10 rounded md:!w-12"
        />
        <div className="min-w-0">
          <p className="truncate text-sm font-medium">{doc.original_filename}</p>
          {tags.length ? (
            <div className="mt-0.5 flex flex-wrap gap-1 md:hidden">
              {tags.slice(0, 2).map((t) => (
                <span
                  key={t}
                  className="rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground"
                >
                  {t}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <div className="hidden md:block">
          <StatusBadge status={doc.status} />
        </div>
        <p className="hidden text-xs text-muted-foreground md:block">
          {formatBytes(doc.file_size_bytes)}
        </p>
        <p className="hidden text-xs text-muted-foreground md:block">
          {doc.page_count ? `${doc.page_count} pages` : "—"}
        </p>
        <p className="hidden text-xs text-muted-foreground md:block">
          {relativeTime(doc.created_at) || "—"}
        </p>
        <div className="flex items-center justify-end gap-1">
          <span className="md:hidden">
            <StatusBadge status={doc.status} />
          </span>
          <DocumentMoreMenu doc={doc} actions={actions} />
        </div>
      </div>
    </DocumentContextMenu>
  );
}
