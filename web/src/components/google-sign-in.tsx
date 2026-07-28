"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";

type Props = {
  onAuthed: (token: string) => void;
  /** Sent on first-time Google signup */
  acceptDisclaimer?: boolean;
  role?: string;
  text?: "signin_with" | "signup_with" | "continue_with";
  onError?: (message: string) => void;
};

let gsiScriptPromise: Promise<void> | null = null;

function loadGsiScript() {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.google?.accounts?.id) return Promise.resolve();
  if (gsiScriptPromise) return gsiScriptPromise;
  gsiScriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[src="https://accounts.google.com/gsi/client"]'
    );
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google script failed")), {
        once: true,
      });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Sign-In"));
    document.head.appendChild(script);
  });
  return gsiScriptPromise;
}

export function GoogleSignIn({
  onAuthed,
  acceptDisclaimer = true,
  role,
  text = "signin_with",
  onError,
}: Props) {
  const btnRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "hidden" | "error">("loading");
  const optsRef = useRef({ onAuthed, acceptDisclaimer, role, onError });
  optsRef.current = { onAuthed, acceptDisclaimer, role, onError };

  useEffect(() => {
    let cancelled = false;

    async function setup() {
      try {
        const clientId =
          (await api<{ enabled: boolean; client_id: string | null }>("/auth/google/config")
            .then((cfg) => (cfg.enabled ? cfg.client_id : null))
            .catch(() => null)) ||
          process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ||
          null;

        if (cancelled) return;
        if (!clientId) {
          setStatus("hidden");
          return;
        }

        await loadGsiScript();
        if (cancelled || !btnRef.current || !window.google?.accounts?.id) return;

        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            const idToken = response.credential;
            if (!idToken) {
              optsRef.current.onError?.("Google did not return a credential.");
              return;
            }
            try {
              const data = await api<{ access_token: string }>("/auth/google", {
                method: "POST",
                json: {
                  id_token: idToken,
                  accept_disclaimer: optsRef.current.acceptDisclaimer,
                  role: optsRef.current.role || undefined,
                },
              });
              optsRef.current.onAuthed(data.access_token);
            } catch (err) {
              optsRef.current.onError?.(
                err instanceof Error ? err.message : "Google sign-in failed"
              );
            }
          },
          auto_select: false,
          cancel_on_tap_outside: true,
        });

        btnRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(btnRef.current, {
          theme: "outline",
          size: "large",
          text,
          shape: "rectangular",
          width: 320,
          logo_alignment: "left",
        });
        setStatus("ready");
      } catch {
        if (!cancelled) setStatus("hidden");
      }
    }

    void setup();
    return () => {
      cancelled = true;
    };
  }, [text]);

  if (status === "hidden") {
    return (
      <p className="text-center text-xs leading-relaxed text-muted-foreground">
        Google Sign-In isn’t configured for this environment. Use email and password, or ask your
        admin to set <span className="font-mono text-foreground/80">GOOGLE_CLIENT_ID</span>.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative flex items-center gap-3 py-1">
        <div className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          or
        </span>
        <div className="h-px flex-1 bg-border" />
      </div>
      {status === "loading" ? (
        <p className="flex items-center justify-center gap-2 text-center text-xs text-muted-foreground">
          <Loader2 className="size-3.5 animate-spin" aria-hidden />
          Loading Google Sign-In…
        </p>
      ) : null}
      <div ref={btnRef} className="flex min-h-[44px] justify-center" />
      <p className="text-center text-[11px] leading-snug text-muted-foreground">
        By continuing with Google, you accept the disclaimer &amp; privacy policy.
      </p>
    </div>
  );
}
