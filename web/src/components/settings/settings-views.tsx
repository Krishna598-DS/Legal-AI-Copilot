"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { z } from "zod";
import {
  Check,
  Copy,
  Loader2,
  Monitor,
  Moon,
  Sun,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { DisclaimerCallout } from "@/components/patterns/disclaimer-callout";
import {
  FormRoot,
  TextFieldInput,
  TextFieldSelect,
  useZodForm,
} from "@/design-system/form";
import { toast } from "@/design-system/toast";
import { api } from "@/lib/api";
import { PERSONA_OPTIONS, routes } from "@/lib/routes";
import {
  createApiKey,
  peekJwtClaims,
  readApiKeys,
  readDevices,
  readNotificationPrefs,
  removeDevice,
  revokeApiKey,
  touchCurrentDevice,
  writeNotificationPrefs,
  type ConnectedDevice,
  type LocalApiKey,
  type NotificationPrefs,
} from "@/lib/settings-prefs";
import { cn } from "@/lib/utils";
import {
  FormStatus,
  IDLE,
  SettingCard,
  SettingsShell,
  type FormStatusState,
} from "./settings-shell";

function failMessage(err: unknown, fallback: string) {
  return err instanceof Error && err.message ? err.message : fallback;
}

/* ─── Profile ─────────────────────────────────────────────────────────── */

const profileSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Enter your name")
    .max(255, "Name is too long"),
  role: z.enum([
    "individual",
    "lawyer",
    "chartered_accountant",
    "business_owner",
    "hr_professional",
    "student",
  ]),
});

export function SettingsProfileView() {
  const { token, user, refreshUser } = useAuth();
  const [status, setStatus] = useState<FormStatusState>(IDLE);
  const form = useZodForm(profileSchema, {
    full_name: user?.full_name || "",
    role: (user?.role as z.infer<typeof profileSchema>["role"]) || "individual",
  });

  useEffect(() => {
    form.reset({
      full_name: user?.full_name || "",
      role: (user?.role as z.infer<typeof profileSchema>["role"]) || "individual",
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset when profile fields change
  }, [user?.full_name, user?.role]);

  return (
    <SettingsShell
      title="Profile"
      description="How you appear in the product. Persona shapes examples and tone — it is not an org role."
    >
      <SettingCard
        title="Your details"
        description="Update your display name and professional persona. Email is used for sign-in and cannot be changed here."
      >
        <FormRoot
          form={form}
          className="max-w-lg space-y-4"
          onSubmit={async (values) => {
            if (!token) return;
            setStatus({ kind: "loading", message: "Saving profile…" });
            try {
              await api("/auth/me", {
                method: "PATCH",
                token,
                json: values,
              });
              await refreshUser();
              setStatus({ kind: "success", message: "Profile saved." });
              toast.success("Profile updated");
            } catch (err) {
              const message = failMessage(err, "Could not save profile");
              setStatus({ kind: "error", message });
              toast.error("Save failed", message);
            }
          }}
        >
          <TextFieldInput
            form={form}
            name="full_name"
            label="Full name"
            description="Shown in the account menu and on exported materials."
            placeholder="Your name"
          />
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="profile-email">
              Email
            </label>
            <Input
              id="profile-email"
              value={user?.email || ""}
              readOnly
              disabled
              aria-describedby="profile-email-hint"
            />
            <p id="profile-email-hint" className="text-xs text-muted-foreground">
              Contact support if you need to change the email on this account.
            </p>
          </div>
          <TextFieldSelect
            form={form}
            name="role"
            label="Persona"
            description="Helps tailor explanations to your context."
            options={PERSONA_OPTIONS.map((o) => ({
              value: o.value,
              label: o.label,
            }))}
          />
          <FormStatus status={status} />
          <div className="flex flex-wrap gap-2 pt-1">
            <Button
              type="submit"
              disabled={status.kind === "loading" || !form.formState.isDirty}
            >
              {status.kind === "loading" ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Saving
                </>
              ) : (
                "Save changes"
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={!form.formState.isDirty || status.kind === "loading"}
              onClick={() => {
                form.reset();
                setStatus(IDLE);
              }}
            >
              Reset
            </Button>
          </div>
        </FormRoot>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Security ────────────────────────────────────────────────────────── */

export function SettingsSecurityView() {
  const { token, user } = useAuth();
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  return (
    <SettingsShell
      title="Security"
      description="Keep your account safe. Verify email, review sign-in options, and manage password from the dedicated page."
    >
      <SettingCard
        title="Email verification"
        description="Verified email protects password resets and account recovery."
      >
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              "inline-flex rounded-md border px-2.5 py-1 text-xs font-medium",
              user?.email_verified
                ? "border-success/30 bg-success/10 text-foreground"
                : "border-warning/40 bg-warning/10 text-foreground"
            )}
          >
            {user?.email_verified ? "Verified" : "Not verified"}
          </span>
          {!user?.email_verified ? (
            <Button
              size="sm"
              variant="secondary"
              disabled={status.kind === "loading" || !token}
              onClick={async () => {
                if (!token) return;
                setStatus({ kind: "loading", message: "Sending verification…" });
                try {
                  await api("/auth/resend-verification", {
                    method: "POST",
                    token,
                  });
                  setStatus({
                    kind: "success",
                    message: "Verification email sent. Check your inbox.",
                  });
                  toast.success("Verification email sent");
                } catch (err) {
                  const message = failMessage(err, "Could not send email");
                  setStatus({ kind: "error", message });
                  toast.error("Send failed", message);
                }
              }}
            >
              Resend verification
            </Button>
          ) : null}
        </div>
        <div className="mt-4">
          <FormStatus status={status} />
        </div>
      </SettingCard>

      <SettingCard
        title="Sign-in methods"
        description="Password accounts can change credentials in Settings → Password. Google accounts manage access through Google."
      >
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            Password:{" "}
            <Link href={routes.settingsPassword} className="text-primary hover:underline">
              Change password
            </Link>
          </li>
          <li>
            Sessions:{" "}
            <Link href={routes.settingsSessions} className="text-primary hover:underline">
              Review active session
            </Link>
          </li>
          <li>
            Forgot password flow:{" "}
            <Link href={routes.forgot} className="text-primary hover:underline">
              Reset via email
            </Link>
          </li>
        </ul>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Password ────────────────────────────────────────────────────────── */

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z
      .string()
      .min(8, "Use at least 8 characters")
      .max(128, "Password is too long"),
    confirm_password: z.string().min(8, "Confirm your new password"),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  })
  .refine((v) => v.current_password !== v.new_password, {
    message: "Choose a different password",
    path: ["new_password"],
  });

export function SettingsPasswordView() {
  const { token } = useAuth();
  const [status, setStatus] = useState<FormStatusState>(IDLE);
  const form = useZodForm(passwordSchema, {
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  return (
    <SettingsShell
      title="Password"
      description="Choose a strong password you do not reuse elsewhere. You will stay signed in on this device after a successful change."
    >
      <SettingCard
        title="Change password"
        description="Enter your current password, then a new one. Google-only accounts cannot set a password here — use Google account recovery instead."
      >
        <FormRoot
          form={form}
          className="max-w-md space-y-4"
          onSubmit={async (values) => {
            if (!token) return;
            setStatus({ kind: "loading", message: "Updating password…" });
            try {
              await api("/auth/change-password", {
                method: "POST",
                token,
                json: values,
              });
              form.reset();
              setStatus({ kind: "success", message: "Password updated." });
              toast.success("Password updated");
            } catch (err) {
              const message = failMessage(err, "Could not update password");
              setStatus({ kind: "error", message });
              toast.error("Update failed", message);
            }
          }}
        >
          <TextFieldInput
            form={form}
            name="current_password"
            type="password"
            label="Current password"
            description="Required to prove it is you."
          />
          <TextFieldInput
            form={form}
            name="new_password"
            type="password"
            label="New password"
            description="At least 8 characters."
          />
          <TextFieldInput
            form={form}
            name="confirm_password"
            type="password"
            label="Confirm new password"
          />
          <FormStatus status={status} />
          <Button type="submit" disabled={status.kind === "loading"}>
            {status.kind === "loading" ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Updating
              </>
            ) : (
              "Update password"
            )}
          </Button>
        </FormRoot>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── API Keys ────────────────────────────────────────────────────────── */

export function SettingsApiKeysView() {
  const { user } = useAuth();
  const userId = user?.id || user?.email || "local";
  const [keys, setKeys] = useState<LocalApiKey[]>([]);
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState("");
  const [status, setStatus] = useState<FormStatusState>(IDLE);
  const [revealed, setRevealed] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setKeys(readApiKeys(userId));
  }, [userId]);

  return (
    <SettingsShell
      title="API Keys"
      description="Create personal keys for scripts and local tooling. Keys are stored on this device only until server-side rotatable keys ship."
    >
      <SettingCard
        title="Create a key"
        description="Give the key a short name so you remember where it is used. The full secret is shown once."
      >
        <form
          className="max-w-md space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            const trimmed = name.trim();
            if (trimmed.length < 2) {
              setNameError("Name must be at least 2 characters");
              setStatus({ kind: "error", message: "Fix the name to continue." });
              return;
            }
            if (trimmed.length > 64) {
              setNameError("Name is too long");
              return;
            }
            setNameError("");
            setStatus({ kind: "loading", message: "Creating key…" });
            window.setTimeout(() => {
              const { list, created } = createApiKey(userId, trimmed);
              setKeys(list);
              setRevealed(created.secret || null);
              setName("");
              setStatus({
                kind: "success",
                message: "Key created. Copy it now — it will not be shown again.",
              });
              toast.success("API key created");
            }, 280);
          }}
        >
          <div className="space-y-1.5">
            <label htmlFor="key-name" className="text-sm font-medium">
              Key name
            </label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Local MCP"
              aria-invalid={Boolean(nameError)}
              aria-describedby={nameError ? "key-name-error" : "key-name-hint"}
            />
            {nameError ? (
              <p id="key-name-error" className="text-xs text-destructive" role="alert">
                {nameError}
              </p>
            ) : (
              <p id="key-name-hint" className="text-xs text-muted-foreground">
                Letters and numbers work best.
              </p>
            )}
          </div>
          <FormStatus status={status} />
          <Button type="submit" disabled={status.kind === "loading"}>
            {status.kind === "loading" ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Creating
              </>
            ) : (
              "Create key"
            )}
          </Button>
        </form>

        {revealed ? (
          <div className="mt-5 rounded-lg border border-primary/30 bg-primary/5 p-3">
            <p className="text-xs font-medium text-foreground">New secret</p>
            <code className="mt-2 block break-all font-mono text-xs text-foreground">
              {revealed}
            </code>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="mt-3"
              onClick={async () => {
                await navigator.clipboard.writeText(revealed);
                setCopied(true);
                toast.success("Copied to clipboard");
                window.setTimeout(() => setCopied(false), 1500);
              }}
            >
              {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
              {copied ? "Copied" : "Copy secret"}
            </Button>
          </div>
        ) : null}
      </SettingCard>

      <SettingCard
        title="Your keys"
        description="Revoking removes the key from this browser. It does not invalidate your signed-in session JWT."
      >
        {keys.length === 0 ? (
          <p className="text-sm text-muted-foreground">No keys yet.</p>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border">
            {keys.map((k) => (
              <li
                key={k.id}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground">{k.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">{k.prefix}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Created {new Date(k.createdAt).toLocaleString()}
                  </p>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive"
                  onClick={() => {
                    setKeys(revokeApiKey(userId, k.id));
                    toast.info("Key revoked");
                    setStatus({ kind: "success", message: `Revoked “${k.name}”.` });
                  }}
                >
                  <Trash2 className="size-3.5" />
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── MCP ─────────────────────────────────────────────────────────────── */

export function SettingsMcpView() {
  const { token } = useAuth();
  const [status, setStatus] = useState<FormStatusState>(IDLE);
  const [copied, setCopied] = useState<"url" | "token" | null>(null);
  // NEXT_PUBLIC_API_URL first — local dev runs the frontend (next dev) and backend
  // (uvicorn) on different ports, so window.location.origin (the frontend's own
  // port) would build an MCP URL that 404s. Production has no such env var and is
  // genuinely same-origin, where window.location.origin is correct.
  const origin =
    process.env.NEXT_PUBLIC_API_URL ||
    (typeof window !== "undefined" ? window.location.origin : "https://your-host");

  // Trailing slash required: the mount only matches "/mcp/..." — a request to the
  // bare "/mcp" path falls through to the SPA catch-all instead (confirmed: it
  // 200s with the marketing page's HTML for GET, 405s for POST).
  const mcpUrl = `${origin.replace(/\/$/, "")}/mcp/`;
  const snippet = useMemo(
    () =>
      JSON.stringify(
        {
          mcpServers: {
            "ai-legal-copilot": {
              url: mcpUrl,
              headers: {
                Authorization: "Bearer <your-access-token>",
              },
            },
          },
        },
        null,
        2
      ),
    [mcpUrl]
  );

  async function copy(kind: "url" | "token" | "snippet", value: string) {
    setStatus({ kind: "loading", message: "Copying…" });
    try {
      await navigator.clipboard.writeText(value);
      if (kind === "url" || kind === "token") setCopied(kind);
      setStatus({ kind: "success", message: "Copied to clipboard." });
      toast.success("Copied");
      window.setTimeout(() => setCopied(null), 1500);
    } catch {
      setStatus({ kind: "error", message: "Clipboard unavailable in this browser." });
    }
  }

  return (
    <SettingsShell
      title="MCP"
      description="Connect Claude Desktop, Cursor, and other MCP clients to the same document tools under your permissions."
    >
      <SettingCard
        title="HTTP endpoint"
        description="Point your MCP client at this URL when the server is enabled on your deployment."
      >
        <div className="flex flex-wrap items-center gap-2">
          <code className="rounded-md border border-border bg-muted/40 px-2.5 py-1.5 font-mono text-xs">
            {mcpUrl}
          </code>
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => void copy("url", mcpUrl)}
          >
            {copied === "url" ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            Copy URL
          </Button>
        </div>
      </SettingCard>

      <SettingCard
        title="Access token"
        description="Use your current session token for local MCP testing. Prefer a dedicated API key for long-lived clients when available."
      >
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            disabled={!token}
            onClick={() => token && void copy("token", token)}
          >
            {copied === "token" ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
            Copy session token
          </Button>
          <Button type="button" size="sm" variant="outline" asChild>
            <Link href={routes.settingsApiKeys}>Manage API keys</Link>
          </Button>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Session tokens expire. Do not commit them to git or share them in chat.
        </p>
        <FormStatus status={status} />
      </SettingCard>

      <SettingCard
        title="Client config"
        description="Example MCP client fragment. Replace the bearer token with your key."
      >
        <pre className="overflow-x-auto rounded-lg border border-border bg-muted/30 p-3 font-mono text-[11px] leading-relaxed text-foreground">
          {snippet}
        </pre>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="mt-3"
          onClick={() => void copy("snippet", snippet)}
        >
          <Copy className="size-3.5" />
          Copy config
        </Button>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Notifications ───────────────────────────────────────────────────── */

export function SettingsNotificationsView() {
  const [prefs, setPrefs] = useState<NotificationPrefs>(readNotificationPrefs);
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  function update<K extends keyof NotificationPrefs>(key: K, value: boolean) {
    const next = { ...prefs, [key]: value };
    setPrefs(next);
    setStatus({ kind: "loading", message: "Saving preferences…" });
    window.setTimeout(() => {
      writeNotificationPrefs(next);
      setStatus({ kind: "success", message: "Preferences saved on this device." });
      toast.success("Notifications updated");
    }, 200);
  }

  const rows: {
    key: keyof NotificationPrefs;
    label: string;
    hint: string;
  }[] = [
    {
      key: "documentReady",
      label: "Document ready",
      hint: "When ingestion finishes and a file is ready to ask.",
    },
    {
      key: "documentFailed",
      label: "Processing failed",
      hint: "When a document fails to process.",
    },
    {
      key: "emailVerifyReminders",
      label: "Verify email reminders",
      hint: "Gentle nudges until your email is verified.",
    },
    {
      key: "productTips",
      label: "Product tips",
      hint: "Occasional tips about Ask, Read, and Risks. Off by default.",
    },
  ];

  return (
    <SettingsShell
      title="Notifications"
      description="Choose which in-app alerts you want. Preferences are saved on this device."
    >
      <SettingCard
        title="In-app alerts"
        description="These control the notification menu on the home screen. Email digests are not enabled yet."
      >
        <ul className="divide-y divide-border rounded-lg border border-border">
          {rows.map((row) => (
            <li
              key={row.key}
              className="flex items-start justify-between gap-4 px-3 py-3"
            >
              <div className="min-w-0">
                <label
                  htmlFor={`notif-${row.key}`}
                  className="text-sm font-medium text-foreground"
                >
                  {row.label}
                </label>
                <p className="mt-0.5 text-xs text-muted-foreground">{row.hint}</p>
              </div>
              <Switch
                id={`notif-${row.key}`}
                checked={prefs[row.key]}
                onCheckedChange={(v) => update(row.key, v)}
                aria-describedby={`notif-hint-${row.key}`}
              />
            </li>
          ))}
        </ul>
        <div className="mt-4">
          <FormStatus status={status} />
        </div>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Theme ───────────────────────────────────────────────────────────── */

export function SettingsThemeView() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  useEffect(() => setMounted(true), []);

  const options = [
    { id: "light", label: "Light", icon: Sun, hint: "Bright surfaces for daytime work." },
    { id: "dark", label: "Dark", icon: Moon, hint: "Lower glare for long review sessions." },
    { id: "system", label: "System", icon: Monitor, hint: "Follow your OS appearance." },
  ] as const;

  return (
    <SettingsShell
      title="Theme"
      description="Pick a comfortable appearance. Your choice syncs across tabs on this browser."
    >
      <SettingCard
        title="Appearance"
        description="Changes apply immediately. System follows your operating system preference."
      >
        {!mounted ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
            <Loader2 className="size-4 animate-spin" />
            Loading theme…
          </div>
        ) : (
          <div
            className="grid gap-3 sm:grid-cols-3"
            role="radiogroup"
            aria-label="Theme"
          >
            {options.map((opt) => {
              const Icon = opt.icon;
              const selected = (theme || "system") === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => {
                    setStatus({ kind: "loading", message: "Applying theme…" });
                    setTheme(opt.id);
                    window.setTimeout(() => {
                      setStatus({
                        kind: "success",
                        message: `Theme set to ${opt.label.toLowerCase()}.`,
                      });
                      toast.success(`Theme: ${opt.label}`);
                    }, 150);
                  }}
                  className={cn(
                    "rounded-xl border p-4 text-left transition-colors",
                    selected
                      ? "border-primary/50 bg-primary/10"
                      : "border-border hover:bg-muted/40"
                  )}
                >
                  <Icon className="size-5 text-foreground" aria-hidden />
                  <p className="mt-3 text-sm font-semibold">{opt.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{opt.hint}</p>
                </button>
              );
            })}
          </div>
        )}
        <p className="mt-4 text-xs text-muted-foreground">
          Currently showing: {mounted ? resolvedTheme || "—" : "—"}
        </p>
        <div className="mt-3">
          <FormStatus status={status} />
        </div>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Account ─────────────────────────────────────────────────────────── */

export function SettingsAccountView() {
  const { user, usage, usageLabel, refreshUsage } = useAuth();
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  useEffect(() => {
    setStatus({ kind: "loading", message: "Loading usage…" });
    void refreshUsage()
      .then(() => setStatus({ kind: "success", message: "Usage up to date." }))
      .catch((err) =>
        setStatus({
          kind: "error",
          message: failMessage(err, "Could not load usage"),
        })
      );
  }, [refreshUsage]);

  return (
    <SettingsShell
      title="Account"
      description="Plan, usage limits, and legal information for this account."
    >
      <SettingCard
        title="Plan"
        description="Your current entitlement. Billing upgrades appear here when enabled."
      >
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-muted-foreground">Plan</dt>
            <dd className="mt-1 font-medium capitalize">{user?.plan || "free"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Documents</dt>
            <dd className="mt-1 font-medium">{user?.document_count ?? "—"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Member since</dt>
            <dd className="mt-1 font-medium">
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString()
                : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Email</dt>
            <dd className="mt-1 font-medium">{user?.email}</dd>
          </div>
        </dl>
      </SettingCard>

      <SettingCard
        title="Usage"
        description="Rolling hourly limits protect shared capacity. Counts refresh when you open this page."
      >
        <FormStatus status={status} />
        {usage ? (
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            <li>
              Questions (last hour): {usage.questions_last_hour} / {usage.questions_limit}
            </li>
            <li>
              Uploads (last hour): {usage.uploads_last_hour} / {usage.uploads_limit}
            </li>
            <li>
              Documents: {usage.documents_owned} / {usage.documents_limit}
            </li>
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">
            {usageLabel || "Usage unavailable."}
          </p>
        )}
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="mt-4"
          onClick={() => {
            setStatus({ kind: "loading", message: "Refreshing…" });
            void refreshUsage()
              .then(() => {
                setStatus({ kind: "success", message: "Usage refreshed." });
                toast.success("Usage refreshed");
              })
              .catch((err) =>
                setStatus({
                  kind: "error",
                  message: failMessage(err, "Refresh failed"),
                })
              );
          }}
        >
          Refresh usage
        </Button>
      </SettingCard>

      <SettingCard
        title="Legal"
        description="This product provides legal information, not legal advice."
      >
        <DisclaimerCallout />
        <p className="mt-3 text-sm text-muted-foreground">
          <a href="/account/privacy" className="text-primary hover:underline">
            Privacy policy
          </a>
          {" · "}
          <a href="/account/disclaimer" className="text-primary hover:underline">
            Disclaimer
          </a>
          {" · "}
          <Link href={routes.settingsDelete} className="text-primary hover:underline">
            Delete account
          </Link>
        </p>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Delete ──────────────────────────────────────────────────────────── */

export function SettingsDeleteView() {
  const { token, logout } = useAuth();
  const [confirm, setConfirm] = useState("");
  const [ack, setAck] = useState(false);
  const [status, setStatus] = useState<FormStatusState>(IDLE);
  const valid = confirm === "DELETE" && ack;

  return (
    <SettingsShell
      title="Delete account"
      description="Permanently close your account. This cannot be undone."
    >
      <SettingCard
        title="Close account"
        description="Deletes your profile, uploaded documents, indexes, and chat history. Type DELETE and acknowledge the warning to continue."
        danger
      >
        <div className="max-w-md space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="delete-confirm" className="text-sm font-medium">
              Confirmation
            </label>
            <Input
              id="delete-confirm"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value.toUpperCase())}
              placeholder="DELETE"
              autoComplete="off"
              aria-invalid={confirm.length > 0 && confirm !== "DELETE"}
              aria-describedby="delete-hint"
            />
            <p id="delete-hint" className="text-xs text-muted-foreground">
              Type DELETE in capitals exactly.
            </p>
          </div>
          <label className="flex items-start gap-2.5 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={ack}
              onChange={(e) => setAck(e.target.checked)}
            />
            <span className="text-muted-foreground">
              I understand this permanently deletes my data and cannot be reversed.
            </span>
          </label>
          <FormStatus status={status} />
          <Button
            type="button"
            variant="danger"
            disabled={!valid || !token || status.kind === "loading"}
            onClick={async () => {
              if (!token || !valid) return;
              setStatus({ kind: "loading", message: "Deleting account…" });
              try {
                await api("/account", { method: "DELETE", token });
                setStatus({ kind: "success", message: "Account deleted." });
                toast.success("Account deleted");
                await logout();
                window.location.href = routes.signIn;
              } catch (err) {
                const message = failMessage(err, "Delete failed");
                setStatus({ kind: "error", message });
                toast.error("Delete failed", message);
              }
            }}
          >
            {status.kind === "loading" ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Deleting…
              </>
            ) : (
              "Delete my account"
            )}
          </Button>
        </div>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Sessions ────────────────────────────────────────────────────────── */

export function SettingsSessionsView() {
  const { token, logout } = useAuth();
  const claims = useMemo(() => peekJwtClaims(token), [token]);
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  const exp = claims?.exp ? new Date(claims.exp * 1000) : null;
  const issued = claims?.iat ? new Date(claims.iat * 1000) : null;

  return (
    <SettingsShell
      title="Sessions"
      description="Auth today uses a single signed token per browser. Full multi-session revocation arrives with the auth upgrade."
    >
      <SettingCard
        title="This session"
        description="The token currently stored in this browser. Signing out discards it on this device."
      >
        {!token ? (
          <FormStatus status={{ kind: "error", message: "Not signed in." }} />
        ) : (
          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-xs text-muted-foreground">Status</dt>
              <dd className="mt-1 font-medium text-foreground">Active on this device</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Issued</dt>
              <dd className="mt-1 font-medium">
                {issued ? issued.toLocaleString() : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Expires</dt>
              <dd className="mt-1 font-medium">
                {exp ? exp.toLocaleString() : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Subject</dt>
              <dd className="mt-1 truncate font-mono text-xs">
                {claims?.sub || "—"}
              </dd>
            </div>
          </dl>
        )}
        <FormStatus status={status} />
        <Button
          type="button"
          variant="secondary"
          className="mt-4"
          disabled={!token || status.kind === "loading"}
          onClick={async () => {
            setStatus({ kind: "loading", message: "Signing out…" });
            try {
              await logout();
              setStatus({ kind: "success", message: "Signed out." });
              window.location.href = routes.signIn;
            } catch (err) {
              setStatus({
                kind: "error",
                message: failMessage(err, "Sign out failed"),
              });
            }
          }}
        >
          Sign out this session
        </Button>
      </SettingCard>
    </SettingsShell>
  );
}

/* ─── Devices ─────────────────────────────────────────────────────────── */

export function SettingsDevicesView() {
  const { user } = useAuth();
  const userId = user?.id || user?.email || "local";
  const [devices, setDevices] = useState<ConnectedDevice[]>([]);
  const [status, setStatus] = useState<FormStatusState>(IDLE);

  useEffect(() => {
    setStatus({ kind: "loading", message: "Loading devices…" });
    try {
      const list = touchCurrentDevice(userId);
      setDevices(list);
      setStatus({ kind: "success", message: "Device list updated." });
    } catch {
      setDevices(readDevices(userId));
      setStatus({ kind: "error", message: "Could not update device list." });
    }
  }, [userId]);

  return (
    <SettingsShell
      title="Connected devices"
      description="Browsers that have opened settings while signed in on this account. Stored locally until server-side device trust ships."
    >
      <SettingCard
        title="Recognized browsers"
        description="Removing a device clears its entry here. It does not revoke a remote session — use Sign out on Sessions for that."
      >
        <FormStatus status={status} />
        {devices.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">No devices recorded yet.</p>
        ) : (
          <ul className="mt-4 divide-y divide-border rounded-lg border border-border">
            {devices.map((d) => (
              <li
                key={d.id}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {d.label}
                    {d.current ? (
                      <span className="ml-2 rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground">
                        This device
                      </span>
                    ) : null}
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Last seen {new Date(d.lastSeenAt).toLocaleString()}
                  </p>
                </div>
                {!d.current ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setDevices(removeDevice(userId, d.id));
                      setStatus({
                        kind: "success",
                        message: `Removed ${d.label}.`,
                      });
                      toast.info("Device removed");
                    }}
                  >
                    Remove
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </SettingCard>
    </SettingsShell>
  );
}

/** @deprecated — usage folded into Account */
export function SettingsUsageView() {
  return <SettingsAccountView />;
}

/** @deprecated — integrations folded into MCP */
export function SettingsIntegrationsView() {
  return <SettingsMcpView />;
}

/** @deprecated — privacy/delete split into Account + Delete */
export function SettingsPrivacyView() {
  return <SettingsAccountView />;
}
