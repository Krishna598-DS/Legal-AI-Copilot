"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  FileText,
  MessageSquare,
  Search,
  Sparkles,
  Upload,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/components/providers/auth-provider";
import { personaActions } from "@/lib/dashboard-actions";
import { runAction } from "@/lib/action-destinations";
import { routes } from "@/lib/routes";
import { isReady } from "@/lib/workspace-activity";
import { cn } from "@/lib/utils";

type SearchItem = {
  id: string;
  group: string;
  label: string;
  hint?: string;
  icon: React.ReactNode;
  run: () => void;
};

export function CommandSearch({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { user, docs, readyDocs } = useAuth();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const latestReadyId = readyDocs[0]?.id || null;

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list: SearchItem[] = [];

    list.push({
      id: "upload",
      group: "Actions",
      label: "Upload a document",
      hint: "PDF or TXT",
      icon: <Upload className="size-4" />,
      run: () => router.push(routes.documents),
    });
    list.push({
      id: "docs",
      group: "Actions",
      label: "Browse documents",
      icon: <FileText className="size-4" />,
      run: () => router.push(routes.documents),
    });
    if (latestReadyId) {
      list.push({
        id: "ask",
        group: "Actions",
        label: "Ask about latest document",
        hint: readyDocs[0]?.original_filename,
        icon: <MessageSquare className="size-4" />,
        run: () => router.push(routes.workspace(latestReadyId, "ask")),
      });
    }

    personaActions(user?.role)
      .filter((a) => a.id !== "upload" && a.id !== "search")
      .slice(0, 4)
      .forEach((action) => {
        list.push({
          id: `action-${action.id}`,
          group: "Suggested",
          label: action.title,
          hint: action.kicker,
          icon: <Sparkles className="size-4" />,
          run: () => runAction(action, latestReadyId, (href) => router.push(href)),
        });
      });

    docs.forEach((d) => {
      list.push({
        id: `doc-${d.id}`,
        group: "Documents",
        label: d.original_filename,
        hint: d.status,
        icon: <FileText className="size-4" />,
        run: () =>
          router.push(
            routes.workspace(d.id, isReady(d.status) ? "ask" : "ask")
          ),
      });
    });

    if (!q) return list;
    return list.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.hint?.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q)
    );
  }, [docs, latestReadyId, query, readyDocs, router, user?.role]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActive(0);
      return;
    }
    const t = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  const select = useCallback(
    (index: number) => {
      const item = items[index];
      if (!item) return;
      onOpenChange(false);
      item.run();
    },
    [items, onOpenChange]
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton={false}
        className="gap-0 overflow-hidden p-0 sm:max-w-lg"
      >
        <DialogHeader className="sr-only">
          <DialogTitle>Search workspace</DialogTitle>
          <DialogDescription>
            Jump to documents, conversations, and actions.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 border-b border-border px-3">
          <Search className="size-4 shrink-0 text-muted-foreground" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search documents and actions…"
            className="h-12 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((i) => Math.min(i + 1, Math.max(items.length - 1, 0)));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((i) => Math.max(i - 1, 0));
              } else if (e.key === "Enter") {
                e.preventDefault();
                select(active);
              }
            }}
          />
          <kbd className="hidden rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground sm:inline">
            esc
          </kbd>
        </div>
        <div className="max-h-[360px] overflow-y-auto p-2">
          {!items.length ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              No matches. Try a document name or “upload”.
            </p>
          ) : (
            (() => {
              let lastGroup = "";
              return items.map((item, index) => {
                const showGroup = item.group !== lastGroup;
                lastGroup = item.group;
                return (
                  <div key={item.id}>
                    {showGroup ? (
                      <p className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                        {item.group}
                      </p>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => select(index)}
                      onMouseEnter={() => setActive(index)}
                      className={cn(
                        "flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm transition-colors",
                        index === active
                          ? "bg-muted text-foreground"
                          : "text-foreground/90 hover:bg-muted/60"
                      )}
                    >
                      <span className="text-muted-foreground">{item.icon}</span>
                      <span className="min-w-0 flex-1 truncate font-medium">
                        {item.label}
                      </span>
                      {item.hint ? (
                        <span className="max-w-[40%] truncate text-xs text-muted-foreground">
                          {item.hint}
                        </span>
                      ) : null}
                    </button>
                  </div>
                );
              });
            })()
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function useCommandSearchShortcut(onOpen: () => void) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpen();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onOpen]);
}
