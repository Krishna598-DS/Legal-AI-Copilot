"use client";

import { FadeIn } from "@/design-system";
import { BrandMark } from "@/components/brand/brand-mark";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

export function AuthBrandMark({ className }: { className?: string }) {
  return <BrandMark href={routes.landing} className={className} />;
}

/** Shared chrome for auth flows — calm, trustworthy, no decoration noise. */
export function AuthShell({
  title,
  description,
  children,
  footer,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen bg-background">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(800px_420px_at_50%_-10%,color-mix(in_oklch,var(--primary)_12%,transparent),transparent_60%)]"
      />
      <div className="relative mx-auto flex min-h-screen w-full max-w-[400px] flex-col justify-center px-5 py-14 sm:px-6">
        <FadeIn>
          <header className="mb-10">
            <AuthBrandMark />
            <h1 className="mt-10 font-display text-2xl font-bold tracking-tight text-foreground sm:text-[1.75rem]">
              {title}
            </h1>
            {description ? (
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                {description}
              </p>
            ) : null}
          </header>
        </FadeIn>
        <FadeIn delay={0.04}>{children}</FadeIn>
        {footer ? (
          <FadeIn delay={0.06}>
            <footer className="mt-10 text-center text-sm text-muted-foreground">
              {footer}
            </footer>
          </FadeIn>
        ) : null}
      </div>
    </div>
  );
}

export function AuthCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-border bg-card p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:p-6",
        className
      )}
    >
      {children}
    </div>
  );
}

export function AuthDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="relative flex items-center gap-3 py-1">
      <div className="h-px flex-1 bg-border" />
      <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

export function AuthTrustNote() {
  return (
    <p className="text-[13px] leading-relaxed text-muted-foreground">
      Legal information, not legal advice. Documents stay private to your account.
    </p>
  );
}
