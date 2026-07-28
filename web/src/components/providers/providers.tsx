"use client";

import { AuthProvider } from "@/components/providers/auth-provider";
import { DesignSystemProvider } from "@/design-system";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <DesignSystemProvider>
      <AuthProvider>{children}</AuthProvider>
    </DesignSystemProvider>
  );
}
