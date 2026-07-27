"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { PanelLeft, Sparkles } from "lucide-react";
import { toast } from "sonner";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Button } from "@/components/ui/button";
import { AiExplainPanel } from "@/components/reader/ai-explain-panel";
import { PdfToolbar } from "@/components/reader/pdf-toolbar";
import { PdfViewer, type SearchHit } from "@/components/reader/pdf-viewer";
import { ReaderSidebar } from "@/components/reader/reader-sidebar";
import {
  addBookmark,
  addNote,
  readAnnotations,
  removeBookmark,
  removeNote,
  type ReaderAnnotations,
} from "@/lib/reader-annotations";
import { workspaceRead } from "@/lib/routes";
import { cn } from "@/lib/utils";

export function PdfReader({
  token,
  documentId,
  filename,
}: {
  token: string | null;
  documentId: string;
  filename?: string | null;
}) {
  const router = useRouter();
  const search = useSearchParams();
  const initialPage = Math.max(1, Number(search.get("page") || 1) || 1);
  const initialQ = search.get("q") || "";

  const [page, setPage] = useState(initialPage);
  const [numPages, setNumPages] = useState(0);
  const [scale, setScale] = useState(1.1);
  const [searchOpen, setSearchOpen] = useState(Boolean(initialQ));
  const [searchQuery, setSearchQuery] = useState(initialQ);
  const [citationQuery, setCitationQuery] = useState(initialQ);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [hitIndex, setHitIndex] = useState(0);
  const [outline, setOutline] = useState<{ title: string; page: number }[]>([]);
  const [annotations, setAnnotations] = useState<ReaderAnnotations>(() =>
    readAnnotations(documentId)
  );
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [aiOpen, setAiOpen] = useState(false);
  const [aiQuote, setAiQuote] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"doc" | "side" | "ai">("doc");

  useEffect(() => {
    setAnnotations(readAnnotations(documentId));
  }, [documentId]);

  useEffect(() => {
    const p = Math.max(1, Number(search.get("page") || 1) || 1);
    const q = search.get("q") || "";
    setPage(p);
    if (q) {
      setCitationQuery(q);
      setSearchQuery(q);
      setSearchOpen(true);
    }
  }, [search]);

  // Fade citation highlight after a few seconds so search can take over
  useEffect(() => {
    if (!citationQuery) return;
    const t = window.setTimeout(() => setCitationQuery(""), 8000);
    return () => window.clearTimeout(t);
  }, [citationQuery]);

  const syncUrl = useCallback(
    (nextPage: number, q?: string) => {
      router.replace(
        workspaceRead(documentId, {
          page: nextPage,
          q: q ?? (citationQuery || searchQuery || null),
        }),
        { scroll: false }
      );
    },
    [router, documentId, citationQuery, searchQuery]
  );

  const onPageChange = useCallback(
    (p: number) => {
      const clamped = Math.min(Math.max(1, p), numPages || p);
      setPage(clamped);
      syncUrl(clamped);
    },
    [numPages, syncUrl]
  );

  const bookmarked = useMemo(
    () => annotations.bookmarks.some((b) => b.page === page),
    [annotations.bookmarks, page]
  );

  const toggleBookmark = useCallback(() => {
    const existing = annotations.bookmarks.find((b) => b.page === page);
    if (existing) {
      setAnnotations(removeBookmark(documentId, existing.id));
      toast.message("Bookmark removed");
    } else {
      setAnnotations(addBookmark(documentId, page));
      toast.success(`Bookmarked page ${page}`);
    }
  }, [annotations.bookmarks, documentId, page]);

  const onSearchQuery = useCallback((q: string) => {
    setSearchQuery(q);
    setCitationQuery("");
    setHitIndex(0);
  }, []);

  const onSearchHits = useCallback((next: SearchHit[]) => {
    setHits(next);
    setHitIndex(0);
  }, []);

  useEffect(() => {
    if (!hits.length) return;
    const hit = hits[hitIndex];
    if (hit) {
      setPage(hit.page);
      syncUrl(hit.page, searchQuery);
    }
    // only when hitIndex / hits identity for navigation
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hitIndex, hits]);

  const goHit = (dir: 1 | -1) => {
    if (!hits.length) return;
    setHitIndex((i) => (i + dir + hits.length) % hits.length);
  };

  const openExplain = (text: string) => {
    setAiQuote(text);
    setAiOpen(true);
    setMobileTab("ai");
  };

  const noteFromSelection = (text: string) => {
    const quote = text.slice(0, 500);
    setAnnotations(
      addNote(documentId, page, quote.length > 120 ? `${quote.slice(0, 120)}…` : quote, quote)
    );
    toast.success("Note saved");
    setSidebarOpen(true);
    setMobileTab("side");
  };

  const askInChat = (prompt: string) => {
    try {
      sessionStorage.setItem("copilot_ask_draft", prompt);
    } catch {
      /* ignore */
    }
    router.push(`/workspace/?id=${encodeURIComponent(documentId)}&mode=ask`);
  };

  return (
    <div className="reader-shell flex h-[min(100dvh-8.5rem,920px)] min-h-[28rem] flex-col overflow-hidden rounded-xl border border-border bg-card shadow-sm">
      <div className="flex items-center gap-2 border-b border-border px-2 py-1.5 md:hidden">
        {(
          [
            { id: "side" as const, label: "Nav" },
            { id: "doc" as const, label: "Document" },
            { id: "ai" as const, label: "Explain" },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setMobileTab(t.id)}
            className={cn(
              "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
              mobileTab === t.id
                ? "bg-primary/15 text-foreground"
                : "text-muted-foreground"
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex min-h-0 flex-1">
        {/* Desktop resizable layout */}
        <div className="hidden min-h-0 min-w-0 flex-1 md:flex">
          <ResizablePanelGroup
            orientation="horizontal"
            className="min-h-0"
            id={`reader-${documentId}`}
          >
            {sidebarOpen ? (
              <>
                <ResizablePanel
                  id="sidebar"
                  defaultSize="18%"
                  minSize="12%"
                  maxSize="32%"
                  collapsible
                  collapsedSize="0%"
                >
                  <ReaderSidebar
                    outline={outline}
                    bookmarks={annotations.bookmarks}
                    notes={annotations.notes}
                    currentPage={page}
                    onJumpPage={onPageChange}
                    onRemoveBookmark={(id) =>
                      setAnnotations(removeBookmark(documentId, id))
                    }
                    onAddNote={(text, p) =>
                      setAnnotations(addNote(documentId, p, text))
                    }
                    onRemoveNote={(id) =>
                      setAnnotations(removeNote(documentId, id))
                    }
                  />
                </ResizablePanel>
                <ResizableHandle withHandle />
              </>
            ) : null}

            <ResizablePanel id="viewer" defaultSize="55%" minSize="35%">
              <div className="flex h-full min-h-0 flex-col">
                <div className="flex items-center gap-1 border-b border-border px-1">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="h-8 w-8 shrink-0 px-0"
                    onClick={() => setSidebarOpen((v) => !v)}
                    aria-label="Toggle sidebar"
                  >
                    <PanelLeft className="size-4" />
                  </Button>
                  <div className="min-w-0 flex-1">
                    <PdfToolbar
                      page={page}
                      numPages={numPages}
                      scale={scale}
                      searchOpen={searchOpen}
                      searchQuery={searchQuery}
                      searchCount={hits.length}
                      searchIndex={hitIndex}
                      bookmarked={bookmarked}
                      onPageChange={onPageChange}
                      onScaleChange={setScale}
                      onToggleSearch={() => setSearchOpen((v) => !v)}
                      onSearchQuery={onSearchQuery}
                      onSearchNext={() => goHit(1)}
                      onSearchPrev={() => goHit(-1)}
                      onToggleBookmark={toggleBookmark}
                      className="border-0"
                    />
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    variant={aiOpen ? "secondary" : "ghost"}
                    className="mr-1 h-8 gap-1.5 px-2"
                    onClick={() => setAiOpen((v) => !v)}
                  >
                    <Sparkles className="size-3.5" />
                    AI
                  </Button>
                </div>
                <PdfViewer
                  token={token}
                  documentId={documentId}
                  filename={filename}
                  page={page}
                  scale={scale}
                  highlightQuery={searchQuery}
                  citationQuery={citationQuery}
                  onNumPages={setNumPages}
                  onPageChange={(p) => {
                    setPage(p);
                  }}
                  onOutline={setOutline}
                  onSearchHits={onSearchHits}
                  onExplain={openExplain}
                  onNoteFromSelection={noteFromSelection}
                  onBookmarkPage={toggleBookmark}
                  className="min-h-0 flex-1"
                />
              </div>
            </ResizablePanel>

            {aiOpen ? (
              <>
                <ResizableHandle withHandle />
                <ResizablePanel
                  id="ai"
                  defaultSize="27%"
                  minSize="18%"
                  maxSize="42%"
                  collapsible
                  collapsedSize="0%"
                >
                  <AiExplainPanel
                    token={token}
                    documentId={documentId}
                    quote={aiQuote}
                    open={aiOpen}
                    onClose={() => setAiOpen(false)}
                    onAskInChat={askInChat}
                  />
                </ResizablePanel>
              </>
            ) : null}
          </ResizablePanelGroup>
        </div>

        {/* Mobile stacked */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col md:hidden">
          {mobileTab === "side" ? (
            <ReaderSidebar
              outline={outline}
              bookmarks={annotations.bookmarks}
              notes={annotations.notes}
              currentPage={page}
              onJumpPage={(p) => {
                onPageChange(p);
                setMobileTab("doc");
              }}
              onRemoveBookmark={(id) =>
                setAnnotations(removeBookmark(documentId, id))
              }
              onAddNote={(text, p) =>
                setAnnotations(addNote(documentId, p, text))
              }
              onRemoveNote={(id) => setAnnotations(removeNote(documentId, id))}
              className="border-r-0"
            />
          ) : null}
          {mobileTab === "doc" ? (
            <div className="flex h-full min-h-0 flex-col">
              <PdfToolbar
                page={page}
                numPages={numPages}
                scale={scale}
                searchOpen={searchOpen}
                searchQuery={searchQuery}
                searchCount={hits.length}
                searchIndex={hitIndex}
                bookmarked={bookmarked}
                onPageChange={onPageChange}
                onScaleChange={setScale}
                onToggleSearch={() => setSearchOpen((v) => !v)}
                onSearchQuery={onSearchQuery}
                onSearchNext={() => goHit(1)}
                onSearchPrev={() => goHit(-1)}
                onToggleBookmark={toggleBookmark}
              />
              <PdfViewer
                token={token}
                documentId={documentId}
                filename={filename}
                page={page}
                scale={scale}
                highlightQuery={searchQuery}
                citationQuery={citationQuery}
                onNumPages={setNumPages}
                onPageChange={setPage}
                onOutline={setOutline}
                onSearchHits={onSearchHits}
                onExplain={openExplain}
                onNoteFromSelection={noteFromSelection}
                onBookmarkPage={toggleBookmark}
                className="min-h-0 flex-1"
              />
            </div>
          ) : null}
          {mobileTab === "ai" ? (
            <AiExplainPanel
              token={token}
              documentId={documentId}
              quote={aiQuote}
              open
              onClose={() => setMobileTab("doc")}
              onAskInChat={askInChat}
              className="border-l-0"
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
