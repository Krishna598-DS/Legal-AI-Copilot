"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

const ROLES = [
  { value: "individual", label: "Individual" },
  { value: "lawyer", label: "Lawyer" },
  { value: "chartered_accountant", label: "Chartered Accountant" },
  { value: "business_owner", label: "Business Owner" },
  { value: "hr_professional", label: "HR Professional" },
  { value: "student", label: "Student" },
];

type Props = {
  onAuthed: (token: string) => void;
};

export function AuthPanel({ onAuthed }: Props) {
  const [tab, setTab] = useState<"login" | "register" | "forgot">("login");
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  async function onLogin(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      const data = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        json: {
          email: fd.get("email"),
          password: fd.get("password"),
        },
      });
      onAuthed(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function onRegister(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    const role = String(fd.get("role") || "");
    if (!role) {
      setError("Please select your role.");
      setBusy(false);
      return;
    }
    try {
      const data = await api<{ access_token: string }>("/auth/register", {
        method: "POST",
        json: {
          email: fd.get("email"),
          password: fd.get("password"),
          full_name: fd.get("full_name") || "",
          role,
          accept_disclaimer: true,
        },
      });
      onAuthed(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  async function onForgot(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setMsg("");
    setBusy(true);
    const fd = new FormData(e.currentTarget);
    try {
      await api("/auth/forgot-password", {
        method: "POST",
        json: { email: fd.get("email") },
      });
      setMsg("If that email exists, a reset was sent.");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function onReset() {
    const token = (document.getElementById("reset-token") as HTMLInputElement)?.value;
    const password = (document.getElementById("reset-password") as HTMLInputElement)
      ?.value;
    setMsg("");
    try {
      await api("/auth/reset-password", {
        method: "POST",
        json: { token, new_password: password },
      });
      setMsg("Password updated. Sign in.");
      setTab("login");
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Reset failed");
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-5 py-12">
      <header className="mb-6">
        <h1 className="font-display text-4xl font-bold tracking-tight text-slate-50">
          AI Legal Copilot
        </h1>
        <p className="mt-3 text-base leading-relaxed text-slate-400">
          Understand legal documents, explain contracts, detect risks, and walk into
          consultations prepared — then connect with the right legal professionals.
        </p>
        <ul className="mt-4 flex flex-wrap gap-2">
          {[
            "Understand documents",
            "Explain contracts",
            "Detect risks",
            "Prepare for counsel",
            "Find professionals",
          ].map((item) => (
            <li
              key={item}
              className="rounded-full border border-teal-700/50 bg-teal-950/40 px-3 py-1 text-xs font-medium text-slate-100"
            >
              {item}
            </li>
          ))}
        </ul>
      </header>

      <div className="mb-4 rounded-lg border-l-4 border-amber-500/80 bg-slate-800/80 px-3 py-2 text-sm leading-relaxed text-slate-300">
        This is legal information, not legal advice. It does not create an attorney–client
        relationship.
      </div>

      <div className="mb-4 flex flex-wrap gap-3 border-b border-slate-700 pb-2">
        {(
          [
            ["login", "Sign in"],
            ["register", "Create account"],
            ["forgot", "Forgot password"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setTab(id);
              setError("");
              setMsg("");
            }}
            className={
              tab === id
                ? "border-b-2 border-teal-400 pb-1 text-slate-50"
                : "pb-1 text-slate-400"
            }
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "login" && (
        <form onSubmit={onLogin} className="space-y-3 rounded-xl border border-slate-700 bg-slate-900/80 p-4">
          <p className="text-sm text-slate-400">Welcome back. Your documents stay private.</p>
          <label className="block text-xs text-slate-400">
            Email
            <Input name="email" type="email" required className="mt-1" autoComplete="email" />
          </label>
          <label className="block text-xs text-slate-400">
            Password
            <Input
              name="password"
              type="password"
              required
              className="mt-1"
              autoComplete="current-password"
            />
          </label>
          <Button type="submit" variant="primary" className="w-full" disabled={busy}>
            Sign in
          </Button>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
        </form>
      )}

      {tab === "register" && (
        <form
          onSubmit={onRegister}
          className="space-y-3 rounded-xl border border-slate-700 bg-slate-900/80 p-4"
        >
          <p className="text-sm text-slate-400">
            Create an account to upload agreements and get plain-language help with citations.
          </p>
          <label className="block text-xs text-slate-400">
            Full name
            <Input name="full_name" className="mt-1" autoComplete="name" />
          </label>
          <label className="block text-xs text-slate-400">
            Email
            <Input name="email" type="email" required className="mt-1" autoComplete="email" />
          </label>
          <label className="block text-xs text-slate-400">
            Password (min 8)
            <Input
              name="password"
              type="password"
              minLength={8}
              required
              className="mt-1"
              autoComplete="new-password"
            />
          </label>
          <label className="block text-xs text-slate-400">
            I am a…
            <select
              name="role"
              required
              defaultValue=""
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm text-slate-100"
            >
              <option value="" disabled>
                Select your role
              </option>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-start gap-2 text-xs text-slate-400">
            <input type="checkbox" name="accept" required className="mt-1" />
            I accept the disclaimer & privacy policy
          </label>
          <Button type="submit" variant="primary" className="w-full" disabled={busy}>
            Create account
          </Button>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
        </form>
      )}

      {tab === "forgot" && (
        <form
          onSubmit={onForgot}
          className="space-y-3 rounded-xl border border-slate-700 bg-slate-900/80 p-4"
        >
          <label className="block text-xs text-slate-400">
            Email
            <Input name="email" type="email" required className="mt-1" />
          </label>
          <Button type="submit" className="w-full" disabled={busy}>
            Send reset link
          </Button>
          <hr className="border-slate-700" />
          <label className="block text-xs text-slate-400">
            Reset token
            <Input id="reset-token" className="mt-1" />
          </label>
          <label className="block text-xs text-slate-400">
            New password
            <Input id="reset-password" type="password" minLength={8} className="mt-1" />
          </label>
          <Button type="button" onClick={onReset} className="w-full">
            Set new password
          </Button>
          {msg ? <p className="text-sm text-slate-400">{msg}</p> : null}
        </form>
      )}
    </div>
  );
}
