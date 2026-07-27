"use client";

import { Folder, FolderOpen, Inbox, Layers } from "lucide-react";
import type { LibraryFolder } from "@/lib/document-meta-store";
import type { FolderScope } from "@/lib/use-document-library";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

function FolderNav({
  folders,
  scope,
  onScope,
  counts,
}: {
  folders: LibraryFolder[];
  scope: FolderScope;
  onScope: (s: FolderScope) => void;
  counts: { all: number; unfiled: number; byFolder: Record<string, number> };
}) {
  const item = (
    id: FolderScope,
    label: string,
    icon: React.ReactNode,
    count: number
  ) => (
    <button
      key={String(id)}
      type="button"
      onClick={() => onScope(id)}
      className={cn(
        "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
        scope === id
          ? "bg-muted font-medium text-foreground"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
      )}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <span className="text-[11px] tabular-nums text-muted-foreground">{count}</span>
    </button>
  );

  return (
    <nav className="space-y-0.5" aria-label="Folders">
      {item("all", "All documents", <Layers className="size-4" />, counts.all)}
      {item(
        "unfiled",
        "Unfiled",
        <Inbox className="size-4" />,
        counts.unfiled
      )}
      {folders.length ? (
        <p className="px-2.5 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          Folders
        </p>
      ) : null}
      {folders.map((f) =>
        item(
          f.id,
          f.name,
          scope === f.id ? (
            <FolderOpen className="size-4" />
          ) : (
            <Folder className="size-4" />
          ),
          counts.byFolder[f.id] || 0
        )
      )}
    </nav>
  );
}

export function FolderSidebar({
  folders,
  scope,
  onScope,
  counts,
  className,
}: {
  folders: LibraryFolder[];
  scope: FolderScope;
  onScope: (s: FolderScope) => void;
  counts: { all: number; unfiled: number; byFolder: Record<string, number> };
  className?: string;
}) {
  return (
    <aside className={cn("hidden w-52 shrink-0 md:block", className)}>
      <FolderNav folders={folders} scope={scope} onScope={onScope} counts={counts} />
    </aside>
  );
}

export function FolderMobileTrigger({
  folders,
  scope,
  onScope,
  counts,
}: {
  folders: LibraryFolder[];
  scope: FolderScope;
  onScope: (s: FolderScope) => void;
  counts: { all: number; unfiled: number; byFolder: Record<string, number> };
}) {
  const label =
    scope === "all"
      ? "All documents"
      : scope === "unfiled"
        ? "Unfiled"
        : folders.find((f) => f.id === scope)?.name || "Folder";

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="md:hidden">
          <Folder className="size-3.5" />
          {label}
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72">
        <SheetHeader>
          <SheetTitle>Folders</SheetTitle>
        </SheetHeader>
        <div className="mt-4">
          <FolderNav folders={folders} scope={scope} onScope={onScope} counts={counts} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
