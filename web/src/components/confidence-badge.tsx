import type { Confidence } from "@/lib/types";
import { cn } from "@/lib/cn";

export function ConfidenceBadge({ data }: { data?: Confidence | null }) {
  if (!data?.confidence_level) return null;
  const level = String(data.confidence_level);
  return (
    <div className="mt-2 space-y-1">
      <span
        className={cn(
          "inline-flex rounded-md border px-2 py-0.5 text-xs font-semibold tracking-wide",
          level.toLowerCase() === "high" &&
            "border-emerald-700 bg-emerald-950 text-emerald-200",
          level.toLowerCase() === "medium" &&
            "border-amber-700 bg-amber-950 text-amber-200",
          level.toLowerCase() === "low" && "border-red-800 bg-red-950 text-red-200"
        )}
      >
        Confidence: {level}
        {data.confidence_score != null
          ? ` · ${Number(data.confidence_score).toFixed(2)}`
          : ""}
      </span>
      {data.recommendation ? (
        <p className="text-xs text-slate-400 leading-relaxed">{data.recommendation}</p>
      ) : null}
    </div>
  );
}
