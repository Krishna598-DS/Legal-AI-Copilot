"use client";

import { cn } from "@/lib/utils";

const DEFAULT_PROMPTS = [
  "What are my payment obligations?",
  "When does this agreement renew or end?",
  "What liabilities or penalties should I watch for?",
  "Summarize the key parties and their roles",
  "What happens if either party wants to terminate?",
];

export function SuggestedPrompts({
  prompts = DEFAULT_PROMPTS,
  onSelect,
  className,
}: {
  prompts?: string[];
  onSelect: (prompt: string) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap justify-center gap-2", className)}>
      {prompts.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => onSelect(p)}
          className="rounded-full border border-border bg-card px-3.5 py-2 text-left text-xs text-muted-foreground transition hover:border-primary/40 hover:bg-muted/40 hover:text-foreground"
        >
          {p}
        </button>
      ))}
    </div>
  );
}

/** Lightweight related follow-ups after an answer — no extra LLM call. */
export function relatedFromTurn(question: string, hasSources: boolean): string[] {
  const q = question.toLowerCase();
  const out: string[] = [];
  if (hasSources) out.push("Show me the exact clause that supports this");
  out.push("Explain that in plain language");
  if (q.includes("pay") || q.includes("fee") || q.includes("rent")) {
    out.push("What late fees or interest apply?");
  } else if (q.includes("terminat") || q.includes("end") || q.includes("renew")) {
    out.push("What notice period is required?");
  } else if (q.includes("liabil") || q.includes("indemn") || q.includes("risk")) {
    out.push("Are there any caps or exclusions on liability?");
  } else {
    out.push("What risks should I watch for here?");
  }
  out.push("What should I ask a lawyer about this?");
  return [...new Set(out)].slice(0, 4);
}

export function RelatedQuestions({
  questions,
  onSelect,
}: {
  questions: string[];
  onSelect: (q: string) => void;
}) {
  if (!questions.length) return null;
  return (
    <div className="mt-3">
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        Related
      </p>
      <div className="flex flex-col gap-1">
        {questions.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onSelect(q)}
            className="rounded-lg border border-transparent px-2.5 py-1.5 text-left text-sm text-primary transition hover:border-border hover:bg-muted/40"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
