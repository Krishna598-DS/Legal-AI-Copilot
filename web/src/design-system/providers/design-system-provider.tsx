"use client";

import { ThemeProvider } from "@/design-system/providers/theme-provider";
import { QueryProvider } from "@/design-system/providers/query-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import { SidebarProvider } from "@/components/ui/sidebar";

export function DesignSystemProvider({
  children,
  withSidebar = false,
}: {
  children: React.ReactNode;
  /** Opt-in: wrap children in SidebarProvider for app shells that use Sidebar. */
  withSidebar?: boolean;
}) {
  const inner = withSidebar ? (
    <SidebarProvider>{children}</SidebarProvider>
  ) : (
    children
  );

  return (
    <ThemeProvider>
      <QueryProvider>
        <TooltipProvider delayDuration={200}>
          {inner}
          <Toaster richColors closeButton position="top-right" />
        </TooltipProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
