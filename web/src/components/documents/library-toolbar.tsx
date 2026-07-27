"use client";

import {
  FolderPlus,
  LayoutGrid,
  List,
  Search,
  ArrowDownAZ,
  Calendar,
  HardDrive,
  CircleDot,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { LibraryPrefs, SortKey, StatusFilter } from "@/lib/document-meta-store";
import { cn } from "@/lib/utils";

const STATUS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "ready", label: "Ready" },
  { id: "processing", label: "Processing" },
  { id: "failed", label: "Failed" },
];

export function LibraryToolbar({
  query,
  onQueryChange,
  statusFilter,
  onStatusFilter,
  tagFilter,
  onTagFilter,
  tagsCatalog,
  prefs,
  onPrefs,
  onNewFolder,
  resultCount,
}: {
  query: string;
  onQueryChange: (q: string) => void;
  statusFilter: StatusFilter;
  onStatusFilter: (s: StatusFilter) => void;
  tagFilter: string | null;
  onTagFilter: (t: string | null) => void;
  tagsCatalog: string[];
  prefs: LibraryPrefs;
  onPrefs: (p: LibraryPrefs) => void;
  onNewFolder: () => void;
  resultCount: number;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[180px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Search documents and tags…"
            className="pl-8"
          />
        </div>
        <div className="flex items-center rounded-lg border border-border p-0.5">
          <Button
            size="icon"
            variant={prefs.view === "grid" ? "secondary" : "ghost"}
            className="size-8"
            aria-label="Grid view"
            onClick={() => onPrefs({ ...prefs, view: "grid" })}
          >
            <LayoutGrid className="size-3.5" />
          </Button>
          <Button
            size="icon"
            variant={prefs.view === "list" ? "secondary" : "ghost"}
            className="size-8"
            aria-label="List view"
            onClick={() => onPrefs({ ...prefs, view: "list" })}
          >
            <List className="size-3.5" />
          </Button>
        </div>
        <Select
          value={prefs.sort}
          onValueChange={(v) => onPrefs({ ...prefs, sort: v as SortKey })}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Sort" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="date">
              <Calendar className="size-3.5" /> Date
            </SelectItem>
            <SelectItem value="name">
              <ArrowDownAZ className="size-3.5" /> Name
            </SelectItem>
            <SelectItem value="size">
              <HardDrive className="size-3.5" /> Size
            </SelectItem>
            <SelectItem value="status">
              <CircleDot className="size-3.5" /> Status
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          onClick={() =>
            onPrefs({
              ...prefs,
              sortDir: prefs.sortDir === "asc" ? "desc" : "asc",
            })
          }
        >
          {prefs.sortDir === "asc" ? "Asc" : "Desc"}
        </Button>
        <Button size="sm" variant="outline" onClick={onNewFolder}>
          <FolderPlus className="size-3.5" />
          Folder
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {STATUS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => onStatusFilter(s.id)}
            className={cn(
              "rounded-md border px-2.5 py-1 text-xs font-medium transition-colors",
              statusFilter === s.id
                ? "border-primary/50 bg-primary/10 text-foreground"
                : "border-border text-muted-foreground hover:bg-muted/50"
            )}
          >
            {s.label}
          </button>
        ))}
        {tagsCatalog.length ? (
          <>
            <span className="mx-1 h-4 w-px bg-border" />
            <button
              type="button"
              onClick={() => onTagFilter(null)}
              className={cn(
                "rounded-md border px-2.5 py-1 text-xs",
                !tagFilter
                  ? "border-primary/50 bg-primary/10"
                  : "border-border text-muted-foreground"
              )}
            >
              All tags
            </button>
            {tagsCatalog.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => onTagFilter(tagFilter === t ? null : t)}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs",
                  tagFilter === t
                    ? "border-primary/50 bg-primary/10"
                    : "border-border text-muted-foreground hover:bg-muted/50"
                )}
              >
                {t}
              </button>
            ))}
          </>
        ) : null}
        <span className="ml-auto text-xs text-muted-foreground">
          {resultCount} document{resultCount === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
}
