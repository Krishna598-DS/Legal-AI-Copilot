"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page } from "react-pdf";
import type { PDFDocumentProxy } from "pdfjs-dist";
import { Loader2 } from "lucide-react";
import { ensurePdfWorker, fetchPdfBlob } from "@/components/reader/pdf-utils";
import { SelectionToolbar } from "@/components/reader/selection-toolbar";
import { cn } from "@/lib/utils";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

export type SearchHit = { page: number; index: number };

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightRenderer(query: string) {
  const q = query.trim();
  if (!q) return undefined;
  const re = new RegExp(`(${escapeRegExp(q)})`, "gi");
  return ({ str }: { str: string }) =>
    str.replace(re, '<mark class="pdf-hl">$1</mark>');
}

export function PdfViewer({
  token,
  documentId,
  filename,
  page,
  scale,
  highlightQuery,
  citationQuery,
  onNumPages,
  onPageChange,
  onOutline,
  onSearchHits,
  onExplain,
  onNoteFromSelection,
  onBookmarkPage,
  className,
}: {
  token: string | null;
  documentId: string;
  filename?: string | null;
  page: number;
  scale: number;
  highlightQuery: string;
  citationQuery: string;
  onNumPages: (n: number) => void;
  onPageChange: (page: number) => void;
  onOutline: (items: { title: string; page: number }[]) => void;
  onSearchHits: (hits: SearchHit[]) => void;
  onExplain: (text: string) => void;
  onNoteFromSelection: (text: string) => void;
  onBookmarkPage: () => void;
  className?: string;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [numPages, setNumPages] = useState(0);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [mounted, setMounted] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const jumping = useRef(false);
  const isTxt = (filename || "").toLowerCase().endsWith(".txt");

  useEffect(() => {
    setMounted(true);
    ensurePdfWorker();
  }, []);

  useEffect(() => {
    if (!token || !documentId) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setLoadError("");
    setBlobUrl(null);
    setPdfDoc(null);

    void (async () => {
      try {
        const blob = await fetchPdfBlob(token, documentId);
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Failed to load file");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, documentId]);

  const activeHighlight = citationQuery.trim() || highlightQuery.trim();

  const customTextRenderer = useMemo(
    () => highlightRenderer(activeHighlight),
    [activeHighlight]
  );

  const scrollToPage = useCallback((p: number, smooth = true) => {
    const el = pageRefs.current.get(p);
    if (!el || !scrollRef.current) return;
    jumping.current = true;
    el.scrollIntoView({
      behavior: smooth ? "smooth" : "instant",
      block: "start",
    });
    window.setTimeout(() => {
      jumping.current = false;
    }, smooth ? 450 : 50);
  }, []);

  useEffect(() => {
    if (!numPages || page < 1) return;
    scrollToPage(page, true);
  }, [page, numPages, scrollToPage]);

  // Search across pages via pdf.js text content
  useEffect(() => {
    if (!pdfDoc || !highlightQuery.trim()) {
      onSearchHits([]);
      return;
    }
    let cancelled = false;
    const q = highlightQuery.trim().toLowerCase();

    void (async () => {
      const hits: SearchHit[] = [];
      for (let p = 1; p <= pdfDoc.numPages; p++) {
        const pageProxy = await pdfDoc.getPage(p);
        const content = await pageProxy.getTextContent();
        const text = content.items
          .map((item) => ("str" in item ? item.str : ""))
          .join(" ")
          .toLowerCase();
        let from = 0;
        let idx = 0;
        while (true) {
          const at = text.indexOf(q, from);
          if (at < 0) break;
          hits.push({ page: p, index: idx++ });
          from = at + q.length;
          if (hits.length > 500) break;
        }
        if (hits.length > 500) break;
      }
      if (!cancelled) onSearchHits(hits);
    })();

    return () => {
      cancelled = true;
    };
  }, [pdfDoc, highlightQuery, onSearchHits]);

  useEffect(() => {
    const root = scrollRef.current;
    if (!root || !numPages) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (jumping.current) return;
        let best: { page: number; ratio: number } | null = null;
        for (const entry of entries) {
          const p = Number((entry.target as HTMLElement).dataset.page);
          if (!p || !entry.isIntersecting) continue;
          if (!best || entry.intersectionRatio > best.ratio) {
            best = { page: p, ratio: entry.intersectionRatio };
          }
        }
        if (best) onPageChange(best.page);
      },
      { root, threshold: [0.35, 0.55, 0.75] }
    );

    pageRefs.current.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [numPages, onPageChange, scale]);

  async function extractOutline(doc: PDFDocumentProxy) {
    try {
      const outline = await doc.getOutline();
      if (!outline?.length) {
        onOutline([]);
        return;
      }
      const items: { title: string; page: number }[] = [];

      async function walk(
        nodes: Awaited<ReturnType<PDFDocumentProxy["getOutline"]>>,
        depth = 0
      ) {
        if (!nodes) return;
        for (const node of nodes) {
          let pageNum = 1;
          try {
            if (node.dest) {
              const dest =
                typeof node.dest === "string"
                  ? await doc.getDestination(node.dest)
                  : node.dest;
              if (Array.isArray(dest) && dest[0]) {
                const idx = await doc.getPageIndex(dest[0]);
                pageNum = idx + 1;
              }
            }
          } catch {
            /* ignore dest resolve errors */
          }
          items.push({
            title: `${"  ".repeat(depth)}${node.title || "Section"}`,
            page: pageNum,
          });
          if (node.items?.length) await walk(node.items, depth + 1);
        }
      }

      await walk(outline);
      onOutline(items.slice(0, 200));
    } catch {
      onOutline([]);
    }
  }

  if (isTxt && blobUrl) {
    return (
      <div className={cn("relative h-full overflow-auto bg-muted/20", className)} ref={scrollRef}>
        <TxtFallback url={blobUrl} />
      </div>
    );
  }

  return (
    <div className={cn("relative flex h-full min-h-0 flex-col", className)}>
      <div
        ref={scrollRef}
        className="reader-scroll relative min-h-0 flex-1 overflow-auto bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-muted/40 via-muted/20 to-background"
      >
        {loading ? (
          <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Opening document…
          </div>
        ) : null}
        {loadError ? (
          <div className="flex h-full items-center justify-center p-6 text-sm text-destructive">
            {loadError}
          </div>
        ) : null}

        {blobUrl && !isTxt && mounted ? (
          <Document
            file={blobUrl}
            loading={null}
            onLoadSuccess={(doc) => {
              setNumPages(doc.numPages);
              onNumPages(doc.numPages);
              setPdfDoc(doc as unknown as PDFDocumentProxy);
              void extractOutline(doc as unknown as PDFDocumentProxy);
            }}
            onLoadError={() => setLoadError("Could not parse PDF")}
            className="mx-auto flex w-full max-w-4xl flex-col items-center gap-4 px-3 py-6 sm:px-6"
          >
            {Array.from({ length: numPages }, (_, i) => i + 1).map((p) => (
              <div
                key={p}
                data-page={p}
                ref={(el) => {
                  if (el) pageRefs.current.set(p, el);
                  else pageRefs.current.delete(p);
                }}
                className={cn(
                  "reader-page w-full max-w-full rounded-sm bg-white shadow-[0_1px_3px_rgba(15,23,42,0.08),0_12px_32px_rgba(15,23,42,0.08)] transition-shadow dark:bg-zinc-950",
                  page === p && "ring-2 ring-primary/30"
                )}
              >
                <div className="flex items-center justify-between border-b border-black/5 px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-zinc-400 dark:border-white/10">
                  <span>Page {p}</span>
                  <span className="font-mono tabular-nums">
                    {p}/{numPages}
                  </span>
                </div>
                <Page
                  pageNumber={p}
                  scale={scale}
                  renderTextLayer
                  renderAnnotationLayer
                  customTextRenderer={customTextRenderer}
                  className="reader-pdf-page"
                  loading={
                    <div className="flex h-[480px] items-center justify-center text-xs text-muted-foreground">
                      <Loader2 className="mr-2 size-3.5 animate-spin" />
                      Rendering…
                    </div>
                  }
                />
              </div>
            ))}
          </Document>
        ) : null}

        <SelectionToolbar
          containerRef={scrollRef}
          onExplain={onExplain}
          onNote={onNoteFromSelection}
          onBookmark={onBookmarkPage}
          onCopy={(text) => void navigator.clipboard.writeText(text)}
        />
      </div>
    </div>
  );
}

function TxtFallback({ url }: { url: string }) {
  const [text, setText] = useState("Loading…");
  useEffect(() => {
    let cancelled = false;
    void fetch(url)
      .then((r) => r.text())
      .then((t) => {
        if (!cancelled) setText(t);
      });
    return () => {
      cancelled = true;
    };
  }, [url]);

  return (
    <pre className="mx-auto max-w-3xl whitespace-pre-wrap px-4 py-8 font-mono text-sm leading-relaxed text-foreground">
      {text}
    </pre>
  );
}
