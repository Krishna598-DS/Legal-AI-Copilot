"use client";

import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  Highlighter,
  Minus,
  Plus,
  Search,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/design-system";
import { cn } from "@/lib/utils";

export function PdfToolbar({
  page,
  numPages,
  scale,
  searchOpen,
  searchQuery,
  searchCount,
  searchIndex,
  bookmarked,
  onPageChange,
  onScaleChange,
  onToggleSearch,
  onSearchQuery,
  onSearchNext,
  onSearchPrev,
  onToggleBookmark,
  className,
}: {
  page: number;
  numPages: number;
  scale: number;
  searchOpen: boolean;
  searchQuery: string;
  searchCount: number;
  searchIndex: number;
  bookmarked: boolean;
  onPageChange: (page: number) => void;
  onScaleChange: (scale: number) => void;
  onToggleSearch: () => void;
  onSearchQuery: (q: string) => void;
  onSearchNext: () => void;
  onSearchPrev: () => void;
  onToggleBookmark: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 border-b border-border bg-background/90 px-3 py-2 backdrop-blur-md",
        className
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-0.5 rounded-lg border border-border bg-muted/30 p-0.5">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 w-8 px-0"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            aria-label="Previous page"
          >
            <ChevronLeft className="size-4" />
          </Button>
          <form
            className="flex items-center gap-1 px-1 text-xs text-muted-foreground"
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              const n = Number(fd.get("page"));
              if (Number.isFinite(n)) onPageChange(n);
            }}
          >
            <input
              key={page}
              name="page"
              type="number"
              min={1}
              max={numPages || 1}
              defaultValue={page}
              className="h-7 w-12 rounded border border-border bg-background px-1 text-center text-xs text-foreground outline-none focus:ring-1 focus:ring-ring"
              aria-label="Page number"
            />
            <span className="whitespace-nowrap">/ {numPages || "—"}</span>
          </form>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 w-8 px-0"
            disabled={!numPages || page >= numPages}
            onClick={() => onPageChange(page + 1)}
            aria-label="Next page"
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>

        <div className="flex items-center gap-0.5 rounded-lg border border-border bg-muted/30 p-0.5">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 w-8 px-0"
            onClick={() => onScaleChange(Math.max(0.5, Math.round((scale - 0.1) * 10) / 10))}
            aria-label="Zoom out"
          >
            <Minus className="size-3.5" />
          </Button>
          <button
            type="button"
            className="min-w-[3.25rem] px-1 text-center text-xs tabular-nums text-muted-foreground hover:text-foreground"
            onClick={() => onScaleChange(1)}
            title="Reset zoom"
          >
            {Math.round(scale * 100)}%
          </button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-8 w-8 px-0"
            onClick={() => onScaleChange(Math.min(2.5, Math.round((scale + 0.1) * 10) / 10))}
            aria-label="Zoom in"
          >
            <Plus className="size-3.5" />
          </Button>
        </div>

        <div className="ml-auto flex items-center gap-1">
          <Button
            type="button"
            size="sm"
            variant={searchOpen ? "secondary" : "ghost"}
            className="h-8 gap-1.5 px-2"
            onClick={onToggleSearch}
          >
            <Search className="size-3.5" />
            <span className="hidden sm:inline">Search</span>
          </Button>
          <Button
            type="button"
            size="sm"
            variant={bookmarked ? "secondary" : "ghost"}
            className="h-8 gap-1.5 px-2"
            onClick={onToggleBookmark}
            title={bookmarked ? "Remove bookmark" : "Bookmark page"}
          >
            <Bookmark className={cn("size-3.5", bookmarked && "fill-current")} />
            <span className="hidden sm:inline">Bookmark</span>
          </Button>
        </div>
      </div>

      {searchOpen ? (
        <div className="flex flex-wrap items-center gap-2 animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="relative min-w-[12rem] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => onSearchQuery(e.target.value)}
              placeholder="Find in document…"
              className="h-9 pl-8 pr-8"
              autoFocus
            />
            {searchQuery ? (
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => onSearchQuery("")}
                aria-label="Clear search"
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
          <span className="text-xs tabular-nums text-muted-foreground">
            {searchQuery
              ? searchCount
                ? `${searchIndex + 1} / ${searchCount}`
                : "No matches"
              : ""}
          </span>
          <div className="flex gap-0.5">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-8 w-8 px-0"
              disabled={!searchCount}
              onClick={onSearchPrev}
              aria-label="Previous match"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              className="h-8 w-8 px-0"
              disabled={!searchCount}
              onClick={onSearchNext}
              aria-label="Next match"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
          {searchQuery ? (
            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              <Highlighter className="size-3" />
              Matches highlighted
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
