"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
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
  TextFieldCheckbox,
  TextFieldInput,
  TextFieldSelect,
  useZodForm,
} from "@/design-system";
import { api } from "@/lib/api";
import { PERSONA_OPTIONS, routes } from "@/lib/routes";

const schema = z.object({
  full_name: z.string().optional(),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Use at least 8 characters"),
  role: z.string().min(1, "Select your role"),
  accept: z.boolean().refine((v) => v === true, "Accept the disclaimer to continue"),
});

type FormValues = z.infer<typeof schema>;

export function SignUpView() {
  const { afterAuth } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const form = useZodForm(schema, {
    full_name: "",
    email: "",
    password: "",
    role: "",
    accept: false,
  });
  const role = form.watch("role");

  async function finish(token: string, emailVerified?: boolean) {
    await afterAuth(token);
    if (emailVerified === false) {
      router.replace(routes.checkEmail({ purpose: "verify", email: form.getValues("email") }));
      return;
    }
    router.replace(routes.home);
  }

  async function onSubmit(values: FormValues) {
    setError("");
    setBusy(true);
    try {
      const data = await api<{ access_token: string; email_verified?: boolean }>(
        "/auth/register",
        {
          method: "POST",
          json: {
            email: values.email,
            password: values.password,
            full_name: values.full_name || "",
            role: values.role,
            accept_disclaimer: true,
          },
        }
      );
      await finish(data.access_token, data.email_verified);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Create your account"
      description="Upload agreements and get cited answers — grounded in your documents."
      footer={
        <>
          Already have an account?{" "}
          <Link href={routes.signIn} className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <div className="relative space-y-5">
        {busy ? <AuthBusyOverlay label="Creating account…" /> : null}
        <AuthTrustNote />
        <AuthCard className="space-y-4">
          {error ? <AuthAlert>{error}</AuthAlert> : null}
          <FormRoot form={form} onSubmit={onSubmit} className="space-y-4">
            <TextFieldInput form={form} name="full_name" label="Full name" />
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
              description="At least 8 characters"
            />
            <TextFieldSelect
              form={form}
              name="role"
              label="I am a…"
              placeholder="Select your role"
              options={PERSONA_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            />
            <TextFieldCheckbox
              form={form}
              name="accept"
              label="I accept the disclaimer and privacy policy"
              description="This product is not a law firm and does not provide legal advice."
            />
            <FormActions>
              <Button type="submit" variant="primary" className="w-full" disabled={busy}>
                Create account
              </Button>
            </FormActions>
          </FormRoot>
          <AuthDivider />
          {role ? (
            <GoogleSignIn
              onAuthed={(t) => void finish(t, true)}
              acceptDisclaimer
              role={role}
              text="signup_with"
              onError={setError}
            />
          ) : (
            <p className="text-center text-body-sm text-muted-foreground">
              Select your role to enable Sign up with Google.
            </p>
          )}
        </AuthCard>
      </div>
    </AuthShell>
  );
}
