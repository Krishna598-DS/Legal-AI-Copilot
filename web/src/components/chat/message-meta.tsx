"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Check,
  Copy,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  BookOpen,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { DisclaimerCallout } from "@/components/patterns/disclaimer-callout";
import type { Citation, Confidence } from "@/lib/types";
import { workspaceRead } from "@/lib/routes";
import { cn } from "@/lib/utils";

export function MessageActions({
  content,
  onRegenerate,
  canRegenerate,
  disabled,
}: {
  content: string;
  onRegenerate?: () => void;
  canRegenerate?: boolean;
  disabled?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="mt-2 flex flex-wrap items-center gap-1 opacity-0 transition-opacity group-hover/msg:opacity-100 focus-within:opacity-100">
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="h-7 gap-1 px-2 text-xs text-muted-foreground"
        onClick={() => void copy()}
        disabled={disabled || !content}
      >
        {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
        {copied ? "Copied" : "Copy"}
      </Button>
      {canRegenerate && onRegenerate ? (
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="h-7 gap-1 px-2 text-xs text-muted-foreground"
          onClick={onRegenerate}
          disabled={disabled}
        >
          <RefreshCw className="size-3" />
          Regenerate
        </Button>
      ) : null}
    </div>
  );
}

export function SourcesPanel({
  sources,
  documentId,
  className,
}: {
  sources?: Citation[];
  documentId?: string | null;
  className?: string;
}) {
  const [open, setOpen] = useState(true);
  if (!sources?.length) return null;

  return (
    <div className={cn("mt-3 rounded-lg border border-border bg-muted/20", className)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <span className="inline-flex items-center gap-1.5">
          <BookOpen className="size-3.5" />
          Sources · {sources.length}
        </span>
        {open ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />}
      </button>
      {open ? (
        <ul className="space-y-2 border-t border-border px-3 py-2.5">
          {sources.map((s, i) => {
            const heading = (
              <>
                [{i + 1}] {s.filename || "Document"}
                {s.page != null ? ` · p.${s.page}` : ""}
              </>
            );
            return (
              <li key={i} className="text-xs leading-relaxed">
                {documentId && s.page != null ? (
                  <Link
                    href={workspaceRead(documentId, {
                      page: s.page,
                      q: s.snippet ? s.snippet.slice(0, 80) : null,
                    })}
                    className="font-medium text-foreground hover:text-primary hover:underline"
                  >
                    {heading}
                  </Link>
                ) : (
                  <p className="font-medium text-foreground">{heading}</p>
                )}
                {s.snippet ? (
                  <p className="mt-0.5 line-clamp-3 text-muted-foreground">
                    {s.snippet}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}

export function CitationChips({
  sources,
  documentId,
  onOpenSources,
}: {
  sources?: Citation[];
  documentId?: string | null;
  onOpenSources?: () => void;
}) {
  if (!sources?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {sources.slice(0, 6).map((s, i) => {
        const label = `${s.filename || "Source"}${s.page != null ? ` p.${s.page}` : ""}`;
        const className =
          "rounded-md border border-border bg-background/80 px-2 py-0.5 text-[11px] text-muted-foreground transition hover:border-primary/40 hover:text-foreground";
        if (documentId && s.page != null) {
          return (
            <Link
              key={i}
              href={workspaceRead(documentId, {
                page: s.page,
                q: s.snippet ? s.snippet.slice(0, 80) : null,
              })}
              className={className}
              title={s.snippet || undefined}
            >
              {label}
            </Link>
          );
        }
        return (
          <button
            key={i}
            type="button"
            onClick={onOpenSources}
            className={className}
            title={s.snippet || undefined}
          >
            {label}
          </button>
        );
      })}
      {sources.length > 6 ? (
        <span className="px-1 text-[11px] text-muted-foreground">
          +{sources.length - 6}
        </span>
      ) : null}
    </div>
  );
}

export function AssistantMeta({
  confidence,
  sources,
  documentId,
}: {
  confidence?: Confidence | null;
  sources?: Citation[];
  documentId?: string | null;
}) {
  return (
    <div className="mt-2 space-y-1">
      <ConfidenceBadge data={confidence} />
      <CitationChips sources={sources} documentId={documentId} />
      <SourcesPanel sources={sources} documentId={documentId} />
      <DisclaimerCallout className="mt-2 text-[11px]" />
    </div>
  );
}
