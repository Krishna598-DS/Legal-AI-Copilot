/** Design-system tokens — single source for spacing, type, motion. */

export const spacing = {
  1: "var(--space-1)",
  2: "var(--space-2)",
  3: "var(--space-3)",
  4: "var(--space-4)",
  5: "var(--space-5)",
  6: "var(--space-6)",
  8: "var(--space-8)",
  10: "var(--space-10)",
  12: "var(--space-12)",
} as const;

export const motion = {
  fast: "var(--motion-fast)",
  base: "var(--motion-base)",
  slow: "var(--motion-slow)",
  easeOut: "var(--ease-out)",
} as const;

export const typography = {
  displayXl: "text-display-xl font-display tracking-tight",
  displayLg: "text-display-lg font-display tracking-tight",
  displayMd: "text-display-md font-display tracking-tight",
  titleLg: "text-title-lg",
  titleMd: "text-title-md",
  titleSm: "text-title-sm",
  bodyLg: "text-body-lg",
  bodyMd: "text-body-md",
  bodySm: "text-body-sm",
  labelMd: "text-label-md uppercase tracking-wider text-muted-foreground",
  labelSm: "text-label-sm uppercase tracking-wider text-muted-foreground",
} as const;

export type StatusTone = "neutral" | "success" | "warning" | "danger" | "info";
