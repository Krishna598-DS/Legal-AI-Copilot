"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { AuthAlert } from "@/components/auth/auth-feedback";
import { Button, toast } from "@/design-system";
import { api } from "@/lib/api";
import { routes } from "@/lib/routes";

export function CheckEmailView() {
  const search = useSearchParams();
  const purpose = (search.get("purpose") || "verify") as "verify" | "reset";
  const email = search.get("email") || "";
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [info, setInfo] = useState("");

  const isVerify = purpose === "verify";

  async function resend() {
    if (!token) {
      setInfo("Sign in to resend a verification email.");
      return;
    }
    setBusy(true);
    setInfo("");
    try {
      const data = await api<{ message?: string }>("/auth/resend-verification", {
        method: "POST",
        token,
      });
      setInfo(data.message || "Verification email sent.");
      toast.success("Email sent");
    } catch (err) {
      setInfo(err instanceof Error ? err.message : "Could not resend");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={isVerify ? "Check your email" : "Check your inbox"}
      description={
        isVerify
          ? "We sent a verification link to confirm your address."
          : "If an account exists for that email, reset instructions are on the way."
      }
      footer={
        <Link href={routes.signIn} className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <AuthCard className="space-y-4">
        <AuthAlert tone="info" title={email || "Your email"}>
          {isVerify
            ? "Open the link in the message to verify your account. You can continue using the product meanwhile if verification is optional for this environment."
            : "The link expires for your security. If you don’t see the email, check spam or try again."}
        </AuthAlert>
        {info ? <AuthAlert tone="success">{info}</AuthAlert> : null}
        <div className="flex flex-col gap-2">
          {isVerify ? (
            <Button variant="outline" className="w-full" disabled={busy} onClick={resend}>
              Resend verification email
            </Button>
          ) : (
            <Button variant="outline" className="w-full" asChild>
              <Link href={routes.forgot}>Try another email</Link>
            </Button>
          )}
          <Button variant="primary" className="w-full" asChild>
            <Link href={isVerify ? routes.home : routes.signIn}>
              {isVerify ? "Continue to workspace" : "Return to sign in"}
            </Link>
          </Button>
        </div>
      </AuthCard>
    </AuthShell>
  );
}
