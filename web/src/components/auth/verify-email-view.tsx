"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { AuthAlert, AuthPageLoader } from "@/components/auth/auth-feedback";
import { Button, FadeIn } from "@/design-system";
import { api } from "@/lib/api";
import { routes } from "@/lib/routes";

type State = "loading" | "success" | "error";

export function VerifyEmailView() {
  const search = useSearchParams();
  const token = search.get("token") || "";
  const [state, setState] = useState<State>(token ? "loading" : "error");
  const [message, setMessage] = useState(
    token ? "Verifying your email…" : "This verification link is missing a token."
  );
  const [email, setEmail] = useState("");

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await api<{ message?: string; email?: string }>(
          `/auth/verify-email?token=${encodeURIComponent(token)}`
        );
        if (cancelled) return;
        setState("success");
        setEmail(data.email || "");
        setMessage(data.message || "Email verified successfully.");
      } catch (err) {
        if (cancelled) return;
        setState("error");
        setMessage(err instanceof Error ? err.message : "Verification failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (state === "loading") {
    return <AuthPageLoader label="Verifying your email…" />;
  }

  return (
    <AuthShell
      title={state === "success" ? "Email verified" : "Verification failed"}
      description={
        state === "success"
          ? "Your address is confirmed. You can continue to your workspace."
          : "The link may be invalid or expired. Request a new one from your account."
      }
      footer={
        <Link href={routes.signIn} className="font-medium text-primary hover:underline">
          Sign in
        </Link>
      }
    >
      <FadeIn>
        <AuthCard className="space-y-4">
          <AuthAlert
            tone={state === "success" ? "success" : "error"}
            title={state === "success" ? "You’re all set" : "Couldn’t verify"}
          >
            {message}
            {email ? (
              <p className="mt-1 text-muted-foreground">
                Confirmed: <span className="text-foreground">{email}</span>
              </p>
            ) : null}
          </AuthAlert>
          <div className="flex flex-col gap-2">
            {state === "success" ? (
              <Button variant="primary" className="w-full" asChild>
                <Link href={routes.home}>Continue</Link>
              </Button>
            ) : (
              <>
                <Button variant="primary" className="w-full" asChild>
                  <Link href={routes.signIn}>Sign in</Link>
                </Button>
                <Button variant="outline" className="w-full" asChild>
                  <Link href={routes.checkEmail({ purpose: "verify" })}>
                    Resend instructions
                  </Link>
                </Button>
              </>
            )}
          </div>
        </AuthCard>
      </FadeIn>
    </AuthShell>
  );
}
