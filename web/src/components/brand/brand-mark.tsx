"use client";

import Link from "next/link";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

/** Product mark — geometric “L” ledger, not a generic sparkle. */
export function BrandGlyph({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative inline-flex size-7 shrink-0 items-center justify-center rounded-[9px] bg-foreground text-background shadow-sm",
        className
      )}
    >
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="opacity-95">
        <path
          d="M3 2.5h2.2v6.2H11V11H3V2.5Z"
          fill="currentColor"
        />
      </svg>
    </span>
  );
}

export function BrandMark({
  href = routes.landing,
  showWordmark = true,
  className,
  wordmarkClassName,
}: {
  href?: string;
  showWordmark?: boolean;
  className?: string;
  wordmarkClassName?: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className
      )}
    >
      <BrandGlyph className="transition-transform duration-200 group-hover:scale-[1.03]" />
      {showWordmark ? (
        <span
          className={cn(
            "font-display text-[1.05rem] font-bold tracking-tight text-foreground",
            wordmarkClassName
          )}
        >
          Legal Copilot
        </span>
      ) : (
        <span className="sr-only">Legal Copilot</span>
      )}
    </Link>
  );
}
