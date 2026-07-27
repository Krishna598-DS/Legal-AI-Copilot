import { cn } from "@/lib/utils";
import { typography } from "./tokens";

type HeadingTag = "h1" | "h2" | "h3" | "h4" | "p" | "span";

const variants = {
  display: typography.displayLg,
  title: typography.titleLg,
  subtitle: typography.titleSm,
  body: typography.bodyMd,
  muted: cn(typography.bodyMd, "text-muted-foreground"),
  label: typography.labelMd,
  kicker: typography.labelSm,
} as const;

export function Text({
  as: Tag = "p",
  variant = "body",
  className,
  ...props
}: React.ComponentProps<"p"> & {
  as?: HeadingTag;
  variant?: keyof typeof variants;
}) {
  return <Tag className={cn(variants[variant], className)} {...props} />;
}

export function Heading({
  level = 1,
  className,
  ...props
}: React.ComponentProps<"h1"> & { level?: 1 | 2 | 3 | 4 }) {
  const Tag = (`h${level}` as const);
  const styles =
    level === 1
      ? typography.displayLg
      : level === 2
        ? typography.displayMd
        : level === 3
          ? typography.titleLg
          : typography.titleMd;
  return <Tag className={cn(styles, className)} {...props} />;
}
