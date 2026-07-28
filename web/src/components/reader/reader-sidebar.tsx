"use client";

import { useState } from "react";
import {
  Bookmark,
  FileText,
  ListTree,
  StickyNote,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReaderBookmark, ReaderNote } from "@/lib/reader-annotations";
import { cn } from "@/lib/utils";

type Tab = "outline" | "bookmarks" | "notes";

export function ReaderSidebar({
  outline,
  bookmarks,
  notes,
  currentPage,
  onJumpPage,
  onRemoveBookmark,
  onAddNote,
  onRemoveNote,
  className,
}: {
  outline: { title: string; page: number }[];
  bookmarks: ReaderBookmark[];
  notes: ReaderNote[];
  currentPage: number;
  onJumpPage: (page: number) => void;
  onRemoveBookmark: (id: string) => void;
  onAddNote: (text: string, page: number) => void;
  onRemoveNote: (id: string) => void;
  className?: string;
}) {
  const [tab, setTab] = useState<Tab>("bookmarks");
  const [draft, setDraft] = useState("");

  const tabs: { id: Tab; label: string; icon: typeof Bookmark }[] = [
    { id: "outline", label: "Outline", icon: ListTree },
    { id: "bookmarks", label: "Marks", icon: Bookmark },
    { id: "notes", label: "Notes", icon: StickyNote },
  ];

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-border bg-muted/15",
        className
      )}
    >
      <div className="flex border-b border-border p-1">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={cn(
                "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                tab === t.id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="size-3.5" />
              <span className="hidden lg:inline">{t.label}</span>
            </button>
          );
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {tab === "outline" ? (
          outline.length ? (
            <ul className="space-y-0.5">
              {outline.map((item, i) => (
                <li key={`${item.page}-${i}`}>
                  <button
                    type="button"
                    onClick={() => onJumpPage(item.page)}
                    className={cn(
                      "flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors hover:bg-muted",
                      currentPage === item.page && "bg-primary/10 text-foreground"
                    )}
                  >
                    <FileText className="mt-0.5 size-3 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 leading-snug">{item.title}</span>
                    <span className="tabular-nums text-muted-foreground">{item.page}</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">
              No outline in this PDF. Use bookmarks instead.
            </p>
          )
        ) : null}

        {tab === "bookmarks" ? (
          bookmarks.length ? (
            <ul className="space-y-1">
              {bookmarks.map((b) => (
                <li
                  key={b.id}
                  className="group flex items-center gap-1 rounded-md border border-transparent px-1 py-1 hover:border-border hover:bg-background"
                >
                  <button
                    type="button"
                    onClick={() => onJumpPage(b.page)}
                    className="min-w-0 flex-1 px-1 text-left text-xs"
                  >
                    <span className="font-medium text-foreground">{b.label}</span>
                    <span className="mt-0.5 block text-[11px] text-muted-foreground">
                      Page {b.page}
                    </span>
                  </button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-7 w-7 shrink-0 px-0 opacity-0 group-hover:opacity-100"
                    onClick={() => onRemoveBookmark(b.id)}
                    aria-label="Remove bookmark"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">
              Bookmark important pages from the toolbar.
            </p>
          )
        ) : null}

        {tab === "notes" ? (
          <div className="space-y-3">
            <form
              className="space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                if (!draft.trim()) return;
                onAddNote(draft.trim(), currentPage);
                setDraft("");
              }}
            >
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                rows={3}
                placeholder={`Note on page ${currentPage}…`}
                className="w-full resize-none rounded-md border border-border bg-background px-2.5 py-2 text-xs leading-relaxed outline-none focus:ring-1 focus:ring-ring"
              />
              <Button type="submit" size="sm" className="w-full" disabled={!draft.trim()}>
                Save note
              </Button>
            </form>
            {notes.length ? (
              <ul className="space-y-2">
                {notes.map((n) => (
                  <li
                    key={n.id}
                    className="rounded-md border border-border bg-background p-2"
                  >
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <button
                        type="button"
                        className="text-[11px] font-medium text-primary hover:underline"
                        onClick={() => onJumpPage(n.page)}
                      >
                        Page {n.page}
                      </button>
                      <button
                        type="button"
                        className="text-muted-foreground hover:text-destructive"
                        onClick={() => onRemoveNote(n.id)}
                        aria-label="Delete note"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </div>
                    {n.quote ? (
                      <p className="mb-1 border-l-2 border-primary/40 pl-2 text-[11px] italic text-muted-foreground line-clamp-2">
                        “{n.quote}”
                      </p>
                    ) : null}
                    <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                      {n.text}
                    </p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-center text-xs text-muted-foreground">
                No notes yet.
              </p>
            )}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
