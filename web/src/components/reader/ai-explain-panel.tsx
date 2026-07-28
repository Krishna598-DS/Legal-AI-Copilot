"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Sparkles, StopCircle, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { apiUrl, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

export function AiExplainPanel({
  token,
  documentId,
  quote,
  open,
  onClose,
  onAskInChat,
  className,
}: {
  token: string | null;
  documentId: string;
  quote: string | null;
  open: boolean;
  onClose: () => void;
  onAskInChat: (prompt: string) => void;
  className?: string;
}) {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }, []);

  const run = useCallback(
    async (text: string) => {
      if (!token || !text.trim()) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      setError("");
      setAnswer("");

      const question = `Explain this passage from the document in plain language. Clarify defined terms and obligations. Do not give legal advice.\n\nPassage:\n"""${text.trim()}"""`;

      try {
        const res = await fetch(apiUrl("/ask/stream"), {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ question, document_id: documentId }),
          signal: controller.signal,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(errorMessage(err, "Explanation failed"));
        }
        const reader = res.body?.getReader();
        if (!reader) throw new Error("No stream");
        const decoder = new TextDecoder();
        let buffer = "";
        let out = "";

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
            const payload = JSON.parse(dataLine) as {
              token?: string;
              answer?: string;
            };
            if (event === "token") {
              out += payload.token || "";
              setAnswer(out);
            }
            if (event === "done") {
              out = payload.answer || out;
              setAnswer(out);
            }
          }
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Explanation failed");
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setLoading(false);
      }
    },
    [token, documentId]
  );

  useEffect(() => {
    if (!open || !quote) return;
    void run(quote);
    return () => {
      abortRef.current?.abort();
    };
  }, [open, quote, run]);

  useEffect(() => () => stop(), [stop]);

  if (!open) return null;

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-l border-border bg-background",
        className
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="size-4 shrink-0 text-primary" />
          <h2 className="truncate text-sm font-semibold tracking-tight">
            AI explanation
          </h2>
        </div>
        <div className="flex items-center gap-1">
          {loading ? (
            <Button type="button" size="sm" variant="ghost" className="h-8 px-2" onClick={stop}>
              <StopCircle className="size-3.5" />
            </Button>
          ) : null}
          <Button type="button" size="sm" variant="ghost" className="h-8 w-8 px-0" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {quote ? (
        <blockquote className="mx-3 mt-3 border-l-2 border-primary/50 bg-muted/30 px-3 py-2 text-xs italic leading-relaxed text-muted-foreground">
          “{quote.length > 320 ? `${quote.slice(0, 320)}…` : quote}”
        </blockquote>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {loading && !answer ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Reading the document…
          </div>
        ) : null}
        {error ? <p className="text-sm text-destructive">{error}</p> : null}
        {answer ? (
          <div className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed prose-p:my-2 prose-headings:font-display">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
            {loading ? (
              <span className="ml-0.5 inline-block h-3 w-1.5 animate-pulse bg-primary/70 align-middle" />
            ) : null}
          </div>
        ) : null}
        {!loading && !answer && !error ? (
          <p className="text-sm text-muted-foreground">
            Select text in the document and choose Explain.
          </p>
        ) : null}
      </div>

      {quote ? (
        <div className="border-t border-border p-3">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            className="w-full"
            onClick={() =>
              onAskInChat(
                `Regarding this passage: "${quote.slice(0, 400)}" — `
              )
            }
          >
            Continue in Ask
          </Button>
        </div>
      ) : null}
    </aside>
  );
}
