"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import {
  AuthCard,
  AuthShell,
  AuthTrustNote,
} from "@/components/auth/auth-shell";
import { AuthAlert, AuthBusyOverlay } from "@/components/auth/auth-feedback";
import {
  Button,
  FormActions,
  FormRoot,
  TextFieldInput,
  useZodForm,
} from "@/design-system";
import { api } from "@/lib/api";
import { routes } from "@/lib/routes";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
});

type FormValues = z.infer<typeof schema>;

export function ForgotPasswordView() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const form = useZodForm(schema, { email: "" });

  async function onSubmit(values: FormValues) {
    setError("");
    setBusy(true);
    try {
      await api("/auth/forgot-password", {
        method: "POST",
        json: { email: values.email },
      });
      router.replace(routes.checkEmail({ purpose: "reset", email: values.email }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      description="Enter your email and we’ll send reset instructions if an account exists."
      footer={
        <Link href={routes.signIn} className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <div className="relative space-y-5">
        {busy ? <AuthBusyOverlay label="Sending…" /> : null}
        <AuthTrustNote />
        <AuthCard className="space-y-4">
          {error ? <AuthAlert>{error}</AuthAlert> : null}
          <FormRoot form={form} onSubmit={onSubmit} className="space-y-4">
            <TextFieldInput
              form={form}
              name="email"
              label="Email"
              type="email"
              placeholder="you@firm.com"
            />
            <FormActions>
              <Button type="submit" variant="primary" className="w-full" disabled={busy}>
                Send reset link
              </Button>
            </FormActions>
          </FormRoot>
        </AuthCard>
      </div>
    </AuthShell>
  );
}
