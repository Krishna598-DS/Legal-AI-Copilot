"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { AuthPageLoader } from "@/components/auth/auth-feedback";
import { TopNav } from "@/components/layout/top-nav";
import { routes } from "@/lib/routes";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { booting, token, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (booting) return;
    if (!token || !user) {
      const next =
        pathname && pathname !== "/" && pathname !== "/home/"
          ? `?next=${encodeURIComponent(pathname)}`
          : "";
      router.replace(`${routes.signIn}${next}`);
    }
  }, [booting, token, user, router, pathname]);

  if (booting) return <AuthPageLoader label="Loading Copilot…" />;
  if (!token || !user) return <AuthPageLoader label="Redirecting to sign in…" />;

  return (
    <div className="min-h-screen">
      <TopNav />
      {children}
    </div>
  );
}
