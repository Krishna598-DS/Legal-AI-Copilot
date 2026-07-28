/** App routes — static-export friendly (trailing slashes). Workspace uses query params. */

export const routes = {
  landing: "/",
  home: "/home/",
  documents: "/documents/",
  workspace: (id?: string | null, mode: WorkspaceMode = "ask") => {
    const q = new URLSearchParams();
    if (id) q.set("id", id);
    if (mode && mode !== "ask") q.set("mode", mode);
    const qs = q.toString();
    return qs ? `/workspace/?${qs}` : "/workspace/";
  },
  professionals: (opts?: { category?: string; city?: string }) => {
    const q = new URLSearchParams();
    if (opts?.category) q.set("category", opts.category);
    if (opts?.city) q.set("city", opts.city);
    const qs = q.toString();
    return qs ? `/professionals/?${qs}` : "/professionals/";
  },
  settings: "/settings/",
  settingsProfile: "/settings/profile/",
  settingsSecurity: "/settings/security/",
  settingsPassword: "/settings/password/",
  settingsApiKeys: "/settings/api-keys/",
  settingsMcp: "/settings/mcp/",
  settingsNotifications: "/settings/notifications/",
  settingsTheme: "/settings/theme/",
  settingsAccount: "/settings/account/",
  settingsDelete: "/settings/delete/",
  settingsSessions: "/settings/sessions/",
  settingsDevices: "/settings/devices/",
  /** @deprecated Use settingsAccount */
  settingsUsage: "/settings/account/",
  /** @deprecated Use settingsMcp */
  settingsIntegrations: "/settings/mcp/",
  /** @deprecated Use settingsDelete / settingsAccount */
  settingsPrivacy: "/settings/account/",
  admin: "/admin/",
  signIn: "/auth/sign-in/",
  signUp: "/auth/sign-up/",
  forgot: "/auth/forgot/",
  checkEmail: (opts?: { purpose?: "verify" | "reset"; email?: string }) => {
    const q = new URLSearchParams();
    if (opts?.purpose) q.set("purpose", opts.purpose);
    if (opts?.email) q.set("email", opts.email);
    const qs = q.toString();
    return qs ? `/auth/check-email/?${qs}` : "/auth/check-email/";
  },
  verify: (token?: string) =>
    token ? `/auth/verify/?token=${encodeURIComponent(token)}` : "/auth/verify/",
  reset: (token?: string) =>
    token ? `/auth/reset/?token=${encodeURIComponent(token)}` : "/auth/reset/",
} as const;

export type WorkspaceMode =
  | "ask"
  | "read"
  | "explain"
  | "risks"
  | "consult"
  | "compare"
  | "connect";

export const WORKSPACE_MODES: { id: WorkspaceMode; label: string }[] = [
  { id: "ask", label: "Ask" },
  { id: "read", label: "Read" },
  { id: "explain", label: "Explain" },
  { id: "risks", label: "Risks" },
  { id: "consult", label: "Consult" },
  { id: "compare", label: "Compare" },
  { id: "connect", label: "Connect" },
];

export function parseWorkspaceMode(raw: string | null | undefined): WorkspaceMode {
  const m = (raw || "ask").toLowerCase();
  if (
    m === "read" ||
    m === "explain" ||
    m === "risks" ||
    m === "consult" ||
    m === "compare" ||
    m === "connect"
  ) {
    return m;
  }
  return "ask";
}

/** Deep-link into the PDF reader at a page, optionally with a highlight query. */
export function workspaceRead(
  id: string,
  opts?: { page?: number | null; q?: string | null }
) {
  const params = new URLSearchParams();
  params.set("id", id);
  params.set("mode", "read");
  if (opts?.page != null && opts.page > 0) params.set("page", String(opts.page));
  if (opts?.q) params.set("q", opts.q);
  return `/workspace/?${params.toString()}`;
}

export const PERSONA_OPTIONS = [
  { value: "individual", label: "Individual" },
  { value: "lawyer", label: "Lawyer" },
  { value: "chartered_accountant", label: "Chartered Accountant" },
  { value: "business_owner", label: "Business Owner" },
  { value: "hr_professional", label: "HR Professional" },
  { value: "student", label: "Student" },
] as const;
