"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import { useAuth } from "@/components/providers/auth-provider";
import { GoogleSignIn } from "@/components/google-sign-in";
import {
  AuthCard,
  AuthDivider,
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
  password: z.string().min(1, "Password is required"),
});

type FormValues = z.infer<typeof schema>;

export function SignInView() {
  const { afterAuth } = useAuth();
  const router = useRouter();
  const search = useSearchParams();
  const next = search.get("next") || routes.home;
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const form = useZodForm(schema, { email: "", password: "" });

  async function finish(token: string) {
    await afterAuth(token);
    router.replace(next.startsWith("/") ? next : routes.home);
  }

  async function onSubmit(values: FormValues) {
    setError("");
    setBusy(true);
    try {
      const data = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        json: values,
      });
      await finish(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Sign in"
      description="Welcome back. Your documents stay private to your account."
      footer={
        <>
          New here?{" "}
          <Link href={routes.signUp} className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <div className="relative space-y-5">
        {busy ? <AuthBusyOverlay label="Signing in…" /> : null}
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
            <TextFieldInput
              form={form}
              name="password"
              label="Password"
              type="password"
            />
            <div className="-mt-2 flex justify-end">
              <Link href={routes.forgot} className="text-body-sm text-primary hover:underline">
                Forgot password?
              </Link>
            </div>
            <FormActions>
              <Button type="submit" variant="primary" className="w-full" disabled={busy}>
                Sign in
              </Button>
            </FormActions>
          </FormRoot>
          <AuthDivider />
          <GoogleSignIn
            onAuthed={(t) => void finish(t)}
            acceptDisclaimer
            text="signin_with"
            onError={setError}
          />
        </AuthCard>
      </div>
    </AuthShell>
  );
}
