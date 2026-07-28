"use client";

import { Group, Panel, Separator } from "react-resizable-panels";
import { cn } from "@/lib/utils";

export function ResizablePanelGroup({
  className,
  ...props
}: React.ComponentProps<typeof Group>) {
  return (
    <Group
      data-slot="resizable-panel-group"
      className={cn(
        "flex h-full w-full data-[orientation=vertical]:flex-col",
        className
      )}
      {...props}
    />
  );
}

export function ResizablePanel({
  className,
  ...props
}: React.ComponentProps<typeof Panel>) {
  return (
    <Panel
      data-slot="resizable-panel"
      className={cn("min-h-0 min-w-0", className)}
      {...props}
    />
  );
}

export function ResizableHandle({
  withHandle,
  className,
  ...props
}: React.ComponentProps<typeof Separator> & { withHandle?: boolean }) {
  return (
    <Separator
      data-slot="resizable-handle"
      className={cn(
        "relative flex w-px items-center justify-center bg-border transition-colors hover:bg-primary/40",
        "data-[orientation=horizontal]:h-full data-[orientation=horizontal]:w-px",
        "data-[orientation=vertical]:h-px data-[orientation=vertical]:w-full",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
        className
      )}
      {...props}
    >
      {withHandle ? (
        <div className="z-10 flex h-8 w-3 items-center justify-center rounded-sm border border-border bg-background shadow-sm">
          <div className="h-3 w-0.5 rounded-full bg-muted-foreground/50" />
        </div>
      ) : null}
    </Separator>
  );
}
