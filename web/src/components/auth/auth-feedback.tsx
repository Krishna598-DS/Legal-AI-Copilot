"use client";

import { AlertCircle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn } from "@/design-system";

export function AuthAlert({
  tone = "error",
  title,
  children,
  className,
}: {
  tone?: "error" | "success" | "info";
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const Icon =
    tone === "success" ? CheckCircle2 : tone === "info" ? Info : AlertCircle;
  return (
    <FadeIn>
      <div
        role={tone === "error" ? "alert" : "status"}
        className={cn(
          "flex gap-3 rounded-lg border px-3 py-2.5 text-body-sm",
          tone === "error" &&
            "border-destructive/30 bg-destructive/10 text-destructive",
          tone === "success" &&
            "border-success/30 bg-success/10 text-success",
          tone === "info" && "border-border bg-muted/50 text-muted-foreground",
          className
        )}
      >
        <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
        <div className="min-w-0 space-y-0.5">
          {title ? <p className="font-medium text-foreground">{title}</p> : null}
          <div className="leading-relaxed">{children}</div>
        </div>
      </div>
    </FadeIn>
  );
}

export function AuthBusyOverlay({ label = "Please wait…" }: { label?: string }) {
  return (
    <div
      className="absolute inset-0 z-10 flex items-center justify-center rounded-xl bg-background/60 backdrop-blur-[2px]"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-2 text-body-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" aria-hidden />
        {label}
      </div>
    </div>
  );
}

export function AuthPageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 bg-background">
      <div className="relative">
        <span
          aria-hidden
          className="absolute -inset-3 animate-pulse rounded-2xl bg-primary/10"
        />
        <span className="relative inline-flex size-10 items-center justify-center rounded-[11px] bg-foreground text-background shadow-sm">
          <svg width="16" height="16" viewBox="0 0 14 14" fill="none" aria-hidden>
            <path d="M3 2.5h2.2v6.2H11V11H3V2.5Z" fill="currentColor" />
          </svg>
        </span>
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <Loader2 className="size-3.5 animate-spin" aria-hidden />
        {label}
      </div>
    </div>
  );
}
