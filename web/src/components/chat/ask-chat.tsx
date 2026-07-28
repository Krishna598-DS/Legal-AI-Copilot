"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { api, apiUrl, errorMessage } from "@/lib/api";
import type { ChatMessage, Citation, Confidence } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/design-system";
import { MarkdownMessage } from "./markdown-message";
import { TypingIndicator } from "./typing-indicator";
import { AskComposer } from "./ask-composer";
import { AssistantMeta, MessageActions } from "./message-meta";
import {
  RelatedQuestions,
  SuggestedPrompts,
  relatedFromTurn,
} from "./suggested-prompts";
import { cn } from "@/lib/utils";

export type ChatBubble = {
  id: string;
  role: string;
  content: string;
  sources?: Citation[];
  confidence?: Confidence | null;
  streaming?: boolean;
  question?: string; // for assistant: the user question that produced it
};

type DonePayload = Confidence & {
  answer?: string;
  sources?: Citation[];
};

export function AskChat({
  token,
  documentId,
  isReady,
  onUsageRefresh,
}: {
  token: string | null;
  documentId: string;
  isReady: boolean;
  onUsageRefresh?: () => Promise<void> | void;
}) {
  const reduceMotion = useReducedMotion();
  const [draft, setDraft] = useState("");
  const [bubbles, setBubbles] = useState<ChatBubble[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const stickToBottom = useRef(true);

  // Hydrate draft from dashboard
  useEffect(() => {
    const d = sessionStorage.getItem("copilot_ask_draft");
    if (d) {
      setDraft(d);
      sessionStorage.removeItem("copilot_ask_draft");
    }
  }, []);

  // Load history
  useEffect(() => {
    if (!token || !documentId) {
      setBubbles([]);
      setHistoryLoading(false);
      return;
    }
    let cancelled = false;
    setHistoryLoading(true);
    (async () => {
      try {
        const messages = await api<ChatMessage[]>(
          `/documents/${documentId}/messages`,
          { token }
        );
        if (cancelled) return;
        const mapped: ChatBubble[] = [];
        let lastUser = "";
        for (const m of messages) {
          if (m.role === "user") lastUser = m.content;
          mapped.push({
            id: m.id || `${documentId}-${mapped.length}`,
            role: m.role,
            content: m.content,
            sources: (m.sources as Citation[] | undefined) || undefined,
            question: m.role === "assistant" ? lastUser : undefined,
          });
        }
        setBubbles(mapped);
      } catch {
        if (!cancelled) setBubbles([]);
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    })();
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [token, documentId]);

  // Smooth stick-to-bottom scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTo({
      top: el.scrollHeight,
      behavior: reduceMotion ? "auto" : "smooth",
    });
  }, [bubbles, streaming, reduceMotion]);

  const lastAssistant = useMemo(() => {
    for (let i = bubbles.length - 1; i >= 0; i--) {
      if (bubbles[i].role === "assistant") return bubbles[i];
    }
    return null;
  }, [bubbles]);

  const related = useMemo(() => {
    if (!lastAssistant || lastAssistant.streaming || !lastAssistant.content) return [];
    if (lastAssistant.content.startsWith("Error:")) return [];
    return relatedFromTurn(
      lastAssistant.question || "",
      Boolean(lastAssistant.sources?.length)
    );
  }, [lastAssistant]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setBubbles((bs) =>
      bs.map((b) => (b.streaming ? { ...b, streaming: false } : b))
    );
  }, []);

  const runStream = useCallback(
    async (question: string, opts?: { replaceAssistantId?: string }) => {
      if (!token || !documentId || !isReady) return;
      const q = question.trim();
      if (!q) return;

      stickToBottom.current = true;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userId = `u-${Date.now()}`;
      const assistantId = opts?.replaceAssistantId || `a-${Date.now()}`;

      if (opts?.replaceAssistantId) {
        setBubbles((bs) =>
          bs.map((b) =>
            b.id === assistantId
              ? {
                  ...b,
                  content: "",
                  sources: undefined,
                  confidence: null,
                  streaming: true,
                  question: q,
                }
              : b
          )
        );
      } else {
        setBubbles((bs) => [
          ...bs,
          { id: userId, role: "user", content: q },
          {
            id: assistantId,
            role: "assistant",
            content: "",
            streaming: true,
            question: q,
          },
        ]);
      }

      setStreaming(true);
      let answer = "";
      let sources: Citation[] = [];

      try {
        const res = await fetch(apiUrl("/ask/stream"), {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ question: q, document_id: documentId }),
          signal: controller.signal,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(errorMessage(err, "Ask failed"));
        }
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No stream");
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          for (const block of parts) {
            const lines = block.split("\n");
            let event = "message";
            let dataLine = "";
            for (const line of lines) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              if (line.startsWith("data:")) dataLine += line.slice(5).trim();
            }
            if (!dataLine) continue;
            const payload = JSON.parse(dataLine) as DonePayload & {
              token?: string;
              sources?: Citation[];
            };
            if (event === "meta") sources = payload.sources || [];
            if (event === "token") {
              answer += payload.token || "";
              setBubbles((bs) =>
                bs.map((b) =>
                  b.id === assistantId
                    ? { ...b, content: answer, sources, streaming: true }
                    : b
                )
              );
            }
            if (event === "done") {
              answer = payload.answer || answer;
              sources = payload.sources || sources;
              setBubbles((bs) =>
                bs.map((b) =>
                  b.id === assistantId
                    ? {
                        ...b,
                        content: answer,
                        sources,
                        confidence: payload,
                        streaming: false,
                      }
                    : b
                )
              );
            }
          }
        }
        await onUsageRefresh?.();
      } catch (err) {
        if (controller.signal.aborted) {
          setBubbles((bs) =>
            bs.map((b) =>
              b.id === assistantId
                ? {
                    ...b,
                    streaming: false,
                    content: b.content || "Generation stopped.",
                  }
                : b
            )
          );
        } else {
          setBubbles((bs) =>
            bs.map((b) =>
              b.id === assistantId
                ? {
                    ...b,
                    streaming: false,
                    content: `Error: ${err instanceof Error ? err.message : "Ask failed"}`,
                  }
                : b
            )
          );
        }
      } finally {
        setStreaming(false);
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [documentId, isReady, onUsageRefresh, token]
  );

  const send = useCallback(() => {
    const q = draft.trim();
    if (!q || streaming) return;
    setDraft("");
    void runStream(q);
  }, [draft, runStream, streaming]);

  const regenerate = useCallback(() => {
    if (!lastAssistant?.question || streaming) return;
    void runStream(lastAssistant.question, {
      replaceAssistantId: lastAssistant.id,
    });
  }, [lastAssistant, runStream, streaming]);

  async function clearConversation() {
    if (!token || !documentId) return;
    abortRef.current?.abort();
    await api(`/documents/${documentId}/conversation/reset`, {
      method: "POST",
      token,
    });
    setBubbles([]);
  }

  const empty = !historyLoading && !bubbles.length;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-1 pb-4"
        onScroll={(e) => {
          const el = e.currentTarget;
          const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
          stickToBottom.current = dist < 80;
        }}
      >
        <div className="mx-auto max-w-3xl space-y-5 pt-2">
          {historyLoading ? (
            <div className="space-y-4 py-6" role="status" aria-live="polite">
              <p className="sr-only">Loading conversation…</p>
              <div className="ml-auto h-16 w-[70%] animate-pulse rounded-2xl bg-primary/15" />
              <div className="h-24 w-[85%] animate-pulse rounded-2xl bg-muted" />
              <div className="h-20 w-[75%] animate-pulse rounded-2xl bg-muted" />
            </div>
          ) : null}

          {empty && isReady ? (
            <EmptyState
              className="border-0 bg-transparent"
              title="Ask your Copilot"
              description="Cited answers with confidence. The conversation is the focus."
              action={
                <SuggestedPrompts
                  onSelect={(p) => {
                    setDraft(p);
                  }}
                />
              }
            />
          ) : null}

          {bubbles.map((b) => {
            const isUser = b.role === "user";
            const isLastAssistant =
              !isUser && lastAssistant?.id === b.id && !b.streaming;
            return (
              <motion.div
                key={b.id}
                initial={reduceMotion ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.16 }}
                className={cn(
                  "group/msg flex flex-col",
                  isUser ? "items-end" : "items-start"
                )}
              >
                <div
                  className={cn(
                    "max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                    isUser
                      ? "bg-primary text-primary-foreground"
                      : "border border-border bg-card text-foreground"
                  )}
                >
                  {isUser ? (
                    <p className="whitespace-pre-wrap">{b.content}</p>
                  ) : (
                    <>
                      {!b.content && b.streaming ? (
                        <TypingIndicator />
                      ) : (
                        <MarkdownMessage
                          content={b.content}
                          streaming={b.streaming}
                        />
                      )}
                      {!b.streaming &&
                      b.content &&
                      !b.content.startsWith("Error:") ? (
                        <AssistantMeta
                          confidence={b.confidence}
                          sources={b.sources}
                          documentId={documentId}
                        />
                      ) : null}
                    </>
                  )}
                </div>
                {!isUser && !b.streaming && b.content ? (
                  <MessageActions
                    content={b.content}
                    canRegenerate={isLastAssistant}
                    onRegenerate={regenerate}
                    disabled={streaming}
                  />
                ) : null}
                {isLastAssistant ? (
                  <RelatedQuestions
                    questions={related}
                    onSelect={(q) => {
                      setDraft(q);
                      void runStream(q);
                    }}
                  />
                ) : null}
              </motion.div>
            );
          })}
        </div>
      </div>

      <div className="border-t border-border bg-background/90 pt-3 backdrop-blur">
        <div className="mx-auto max-w-3xl space-y-2">
          <AskComposer
            value={draft}
            onChange={setDraft}
            onSubmit={send}
            onStop={stop}
            streaming={streaming}
            disabled={!isReady}
          />
          <div className="flex items-center justify-between pb-2">
            <Button
              size="sm"
              variant="ghost"
              className="text-xs text-muted-foreground"
              disabled={!documentId || streaming}
              onClick={() => void clearConversation()}
            >
              Clear conversation
            </Button>
            {!isReady ? (
              <span className="text-xs text-amber-500">
                Document still processing…
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
