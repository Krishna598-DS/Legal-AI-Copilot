"use client";

import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Standard page width + padding used across authenticated product screens. */
export function PageShell({
  children,
  className,
  wide,
}: {
  children: React.ReactNode;
  className?: string;
  wide?: boolean;
}) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 py-6 sm:px-6 sm:py-8",
        wide ? "max-w-7xl" : "max-w-6xl",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SurfaceCard({
  children,
  className,
  as: Comp = "section",
}: {
  children: React.ReactNode;
  className?: string;
  as?: "section" | "div" | "article" | "li";
}) {
  return (
    <Comp
      className={cn(
        "rounded-xl border border-border bg-card p-4 shadow-sm transition-shadow duration-200 sm:p-5",
        "hover:shadow-md",
        className
      )}
    >
      {children}
    </Comp>
  );
}

export function SurfaceInset({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border/80 bg-muted/25 p-3 sm:p-4",
        className
      )}
    >
      {children}
    </div>
  );
}

export function SegmentedTabs({
  items,
  value,
  onChange,
  ariaLabel,
  className,
}: {
  items: { id: string; label: string; disabled?: boolean }[];
  value: string;
  onChange: (id: string) => void;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "flex gap-0.5 overflow-x-auto rounded-lg border border-border bg-muted/40 p-0.5 scrollbar-none",
        className
      )}
    >
      {items.map((item) => {
        const active = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={active}
            disabled={item.disabled}
            onClick={() => onChange(item.id)}
            className={cn(
              "shrink-0 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
              "disabled:pointer-events-none disabled:opacity-40",
              active
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}

export function StatusBanner({
  tone = "info",
  children,
  className,
}: {
  tone?: "info" | "warning" | "error" | "success";
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="status"
      className={cn(
        "rounded-lg border px-3 py-2.5 text-sm leading-relaxed",
        tone === "info" && "border-border bg-muted/40 text-muted-foreground",
        tone === "warning" &&
          "border-warning/35 bg-warning/10 text-foreground",
        tone === "error" &&
          "border-destructive/35 bg-destructive/10 text-destructive",
        tone === "success" && "border-success/35 bg-success/10 text-foreground",
        className
      )}
    >
      {children}
    </div>
  );
}

export function LoadingBlock({
  label = "Loading…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-center gap-2 rounded-xl border border-dashed border-border bg-muted/20 px-4 py-10 text-sm text-muted-foreground",
        className
      )}
    >
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function ContactChip({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target={href.startsWith("http") ? "_blank" : undefined}
      rel={href.startsWith("http") ? "noreferrer" : undefined}
      className="inline-flex items-center rounded-md border border-border bg-background px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:border-primary/40 hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {children}
    </a>
  );
}

export function PanelHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-base font-semibold tracking-tight text-foreground">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  );
}
