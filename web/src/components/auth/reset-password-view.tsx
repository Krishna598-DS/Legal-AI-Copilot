"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { z } from "zod";
import { AuthCard, AuthShell } from "@/components/auth/auth-shell";
import { AuthAlert, AuthBusyOverlay } from "@/components/auth/auth-feedback";
import {
  Button,
  FormActions,
  FormRoot,
  TextFieldInput,
  useZodForm,
  toast,
} from "@/design-system";
import { api } from "@/lib/api";
import { routes } from "@/lib/routes";

const schema = z
  .object({
    token: z.string().min(1, "Reset token is required"),
    password: z.string().min(8, "Use at least 8 characters"),
    confirm: z.string().min(1, "Confirm your password"),
  })
  .refine((v) => v.password === v.confirm, {
    message: "Passwords do not match",
    path: ["confirm"],
  });

type FormValues = z.infer<typeof schema>;

export function ResetPasswordView() {
  const router = useRouter();
  const search = useSearchParams();
  const initialToken = search.get("token") || "";
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const form = useZodForm(schema, {
    token: initialToken,
    password: "",
    confirm: "",
  });

  async function onSubmit(values: FormValues) {
    setError("");
    setBusy(true);
    try {
      await api("/auth/reset-password", {
        method: "POST",
        json: { token: values.token, new_password: values.password },
      });
      setDone(true);
      toast.success("Password updated", "You can sign in with your new password.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={done ? "Password updated" : "Choose a new password"}
      description={
        done
          ? "Your password has been changed. Sign in to continue."
          : "Use the link from your email, or paste the reset token below."
      }
      footer={
        <Link href={routes.signIn} className="font-medium text-primary hover:underline">
          Back to sign in
        </Link>
      }
    >
      <div className="relative space-y-5">
        {busy ? <AuthBusyOverlay label="Updating password…" /> : null}
        {done ? (
          <AuthCard className="space-y-4">
            <AuthAlert tone="success" title="Success">
              Your password is ready. Continue to sign in.
            </AuthAlert>
            <Button
              variant="primary"
              className="w-full"
              onClick={() => router.push(routes.signIn)}
            >
              Sign in
            </Button>
          </AuthCard>
        ) : (
          <AuthCard className="space-y-4">
            {error ? <AuthAlert>{error}</AuthAlert> : null}
            <FormRoot form={form} onSubmit={onSubmit} className="space-y-4">
              {!initialToken ? (
                <TextFieldInput form={form} name="token" label="Reset token" />
              ) : (
                <input type="hidden" {...form.register("token")} />
              )}
              <TextFieldInput
                form={form}
                name="password"
                label="New password"
                type="password"
                description="At least 8 characters"
              />
              <TextFieldInput
                form={form}
                name="confirm"
                label="Confirm password"
                type="password"
              />
              <FormActions>
                <Button type="submit" variant="primary" className="w-full" disabled={busy}>
                  Set new password
                </Button>
              </FormActions>
            </FormRoot>
          </AuthCard>
        )}
      </div>
    </AuthShell>
  );
}
