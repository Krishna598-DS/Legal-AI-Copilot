import { cn } from "@/lib/utils";
import type { StatusTone } from "@/design-system/tokens";

const toneClass: Record<StatusTone, string> = {
  neutral: "border-border bg-muted text-muted-foreground",
  success:
    "border-success/30 bg-success/10 text-success dark:border-success/40 dark:bg-success/15",
  warning:
    "border-warning/30 bg-warning/10 text-warning-foreground dark:text-warning",
  danger: "border-destructive/30 bg-destructive/10 text-destructive",
  info: "border-primary/30 bg-primary/10 text-primary",
};

/** Map document pipeline status → tone + label. */
export function documentStatusTone(status?: string | null): {
  tone: StatusTone;
  label: string;
} {
  const key = (status || "").toUpperCase();
  if (key === "READY") return { tone: "success", label: "Ready" };
  if (key === "FAILED") return { tone: "danger", label: "Failed" };
  if (key === "PROCESSING" || key === "UPLOADING")
    return {
      tone: "warning",
      label: key === "UPLOADING" ? "Uploading" : "Processing",
    };
  return { tone: "neutral", label: status || "Unknown" };
}

export function StatusBadge({
  tone,
  status,
  children,
  className,
  ...props
}: React.ComponentProps<"span"> & {
  tone?: StatusTone;
  /** Document pipeline status shortcut (READY / FAILED / …). */
  status?: string | null;
}) {
  const mapped = status != null ? documentStatusTone(status) : null;
  const resolvedTone = tone ?? mapped?.tone ?? "neutral";
  const content = children ?? mapped?.label;

  return (
    <span
      data-slot="status-badge"
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold tracking-wide",
        toneClass[resolvedTone],
        className
      )}
      {...props}
    >
      {content}
    </span>
  );
}
