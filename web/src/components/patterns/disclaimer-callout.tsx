import { cn } from "@/lib/utils";

export function DisclaimerCallout({
  children = "This is legal information, not legal advice. It does not create an attorney–client relationship.",
  className = "",
}: {
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="note"
      className={cn(
        "rounded-lg border-l-4 border-warning bg-muted/60 px-3 py-2 text-xs leading-relaxed text-muted-foreground",
        className
      )}
    >
      {children}
    </div>
  );
}
