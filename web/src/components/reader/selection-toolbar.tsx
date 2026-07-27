"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { BookmarkPlus, Copy, MessageSquareText, StickyNote } from "lucide-react";
import { cn } from "@/lib/utils";

export type SelectionPayload = {
  text: string;
  x: number;
  y: number;
};

export function SelectionToolbar({
  containerRef,
  onExplain,
  onNote,
  onBookmark,
  onCopy,
}: {
  containerRef: React.RefObject<HTMLElement | null>;
  onExplain: (text: string) => void;
  onNote: (text: string) => void;
  onBookmark: () => void;
  onCopy: (text: string) => void;
}) {
  const [sel, setSel] = useState<SelectionPayload | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onSelectionChange() {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed || !selection.rangeCount) {
        setSel(null);
        return;
      }
      const text = selection.toString().trim();
      if (text.length < 2) {
        setSel(null);
        return;
      }
      const range = selection.getRangeAt(0);
      const container = containerRef.current;
      if (!container || !container.contains(range.commonAncestorContainer)) {
        setSel(null);
        return;
      }
      const rect = range.getBoundingClientRect();
      const host = container.getBoundingClientRect();
      setSel({
        text,
        x: rect.left + rect.width / 2 - host.left + container.scrollLeft,
        y: rect.top - host.top + container.scrollTop - 8,
      });
    }

    function onMouseDown(e: MouseEvent) {
      if (barRef.current?.contains(e.target as Node)) return;
      window.setTimeout(() => {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) setSel(null);
      }, 0);
    }

    document.addEventListener("selectionchange", onSelectionChange);
    document.addEventListener("mousedown", onMouseDown);
    return () => {
      document.removeEventListener("selectionchange", onSelectionChange);
      document.removeEventListener("mousedown", onMouseDown);
    };
  }, [containerRef]);

  useLayoutEffect(() => {
    if (!sel || !barRef.current || !containerRef.current) return;
    const bar = barRef.current;
    const host = containerRef.current;
    const maxX = host.clientWidth - bar.offsetWidth - 8;
    const left = Math.max(8, Math.min(sel.x - bar.offsetWidth / 2, maxX));
    const top = Math.max(8, sel.y - bar.offsetHeight);
    bar.style.transform = `translate(${left}px, ${top}px)`;
  }, [sel, containerRef]);

  if (!sel) return null;

  const actions = [
    {
      label: "Explain",
      icon: MessageSquareText,
      onClick: () => onExplain(sel.text),
    },
    {
      label: "Note",
      icon: StickyNote,
      onClick: () => onNote(sel.text),
    },
    {
      label: "Mark",
      icon: BookmarkPlus,
      onClick: () => onBookmark(),
    },
    {
      label: "Copy",
      icon: Copy,
      onClick: () => onCopy(sel.text),
    },
  ];

  return (
    <div
      ref={barRef}
      className={cn(
        "pointer-events-auto absolute left-0 top-0 z-30 flex items-center gap-0.5 rounded-lg border border-border bg-popover px-1 py-1 shadow-lg",
        "animate-in fade-in zoom-in-95 duration-150"
      )}
      role="toolbar"
      aria-label="Selection actions"
    >
      {actions.map((a) => {
        const Icon = a.icon;
        return (
          <button
            key={a.label}
            type="button"
            className="inline-flex items-center gap-1 rounded-md px-2 py-1.5 text-xs font-medium text-popover-foreground transition-colors hover:bg-muted"
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              a.onClick();
              window.getSelection()?.removeAllRanges();
              setSel(null);
            }}
          >
            <Icon className="size-3.5" />
            {a.label}
          </button>
        );
      })}
    </div>
  );
}
