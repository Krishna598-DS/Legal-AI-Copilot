"use client";

import { useEffect, useRef } from "react";
import { ArrowUp, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export function AskComposer({
  value,
  onChange,
  onSubmit,
  onStop,
  streaming,
  disabled,
  placeholder = "Ask about this document…",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onStop?: () => void;
  streaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card shadow-sm transition-colors focus-within:border-primary/40"
      )}
    >
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled && !streaming}
        rows={1}
        className="min-h-[44px] resize-none border-0 bg-transparent px-4 py-3 text-sm shadow-none focus-visible:ring-0"
        onKeyDown={(e) => {
          if (e.key === "Escape" && streaming) {
            e.preventDefault();
            onStop?.();
            return;
          }
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            if (streaming) return;
            onSubmit();
          }
        }}
      />
      <div className="flex items-center justify-between gap-2 px-3 pb-2.5">
        <p className="hidden text-[11px] text-muted-foreground sm:block">
          Enter to send · Shift+Enter for newline · Esc to stop
        </p>
        {streaming ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="gap-1.5"
            onClick={onStop}
          >
            <Square className="size-3 fill-current" />
            Stop
          </Button>
        ) : (
          <Button
            type="button"
            size="icon"
            variant="primary"
            className="size-8 rounded-full"
            disabled={disabled || !value.trim()}
            onClick={onSubmit}
            aria-label="Send"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
