"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/providers/auth-provider";
import { AuthPageLoader } from "@/components/auth/auth-feedback";
import { routes } from "@/lib/routes";

/** Auth / landing: bounce signed-in users into the product. */
export function GuestOnly({
  children,
  redirectTo = routes.home,
}: {
  children: React.ReactNode;
  redirectTo?: string;
}) {
  const { booting, token, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!booting && token && user) router.replace(redirectTo);
  }, [booting, token, user, router, redirectTo]);

  if (booting) return <AuthPageLoader label="Loading…" />;
  if (token && user) return <AuthPageLoader label="Taking you in…" />;
  return <>{children}</>;
}
