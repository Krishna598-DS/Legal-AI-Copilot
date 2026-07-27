import type { Confidence } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export function ConfidenceBadge({ data }: { data?: Confidence | null }) {
  if (!data?.confidence_level) return null;
  const level = String(data.confidence_level);
  const factors = data.confidence_factors
    ? Object.entries(data.confidence_factors)
        .map(([k, v]) => `${k}: ${Number(v).toFixed(2)}`)
        .join(" · ")
    : null;

  const badge = (
    <span
      className={cn(
        "inline-flex rounded-md border px-2 py-0.5 text-xs font-semibold tracking-wide",
        level.toLowerCase() === "high" &&
          "border-success/40 bg-success/10 text-success",
        level.toLowerCase() === "medium" &&
          "border-warning/40 bg-warning/10 text-warning",
        level.toLowerCase() === "low" &&
          "border-destructive/40 bg-destructive/10 text-destructive"
      )}
    >
      Confidence: {level}
      {data.confidence_score != null
        ? ` · ${Number(data.confidence_score).toFixed(2)}`
        : ""}
    </span>
  );

  return (
    <div className="mt-2 space-y-1">
      {factors ? (
        <Tooltip>
          <TooltipTrigger asChild>{badge}</TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">{factors}</TooltipContent>
        </Tooltip>
      ) : (
        badge
      )}
      {data.recommendation ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          {data.recommendation}
        </p>
      ) : null}
    </div>
  );
}
