"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { AuthPageLoader } from "@/components/auth/auth-feedback";
import { BrandMark } from "@/components/brand/brand-mark";
import { Button, FadeIn } from "@/design-system";
import { routes } from "@/lib/routes";

export function LandingView() {
  const { booting, token, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!booting && token && user) router.replace(routes.home);
  }, [booting, token, user, router]);

  if (booting) return <AuthPageLoader />;
  if (token && user) return <AuthPageLoader label="Opening your workspace…" />;

  return (
    <div className="relative min-h-screen bg-background">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(900px_500px_at_50%_-20%,color-mix(in_oklch,var(--primary)_14%,transparent),transparent_55%)]"
      />

      <header className="relative mx-auto flex h-16 max-w-5xl items-center justify-between px-5 sm:px-8">
        <BrandMark />
        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Marketing">
          <Button variant="ghost" size="sm" asChild>
            <Link href={routes.signIn}>Sign in</Link>
          </Button>
          <Button variant="primary" size="sm" asChild>
            <Link href={routes.signUp}>Get started</Link>
          </Button>
        </nav>
      </header>

      <main>
        <section className="relative mx-auto flex max-w-5xl flex-col items-center px-5 pb-24 pt-16 text-center sm:px-8 sm:pt-24">
          <FadeIn>
            <p className="text-[12px] font-medium tracking-[0.08em] text-muted-foreground uppercase">
              Legal information · Not legal advice
            </p>
            <h1 className="mt-5 max-w-[18ch] font-display text-[2.75rem] font-bold leading-[1.05] tracking-tight text-foreground sm:text-6xl sm:leading-[1.02]">
              Understand the contract before you sign.
            </h1>
            <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              Upload an agreement. Ask in plain language. Get cited answers with confidence —
              then prepare for a professional when you need one.
            </p>
            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <Button variant="primary" size="lg" asChild>
                <Link href={routes.signUp}>
                  Start free
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" asChild>
                <Link href={routes.signIn}>Sign in</Link>
              </Button>
            </div>
          </FadeIn>

          <FadeIn delay={0.1}>
            <div className="relative mt-16 w-full max-w-3xl">
              <div
                aria-hidden
                className="absolute -inset-px rounded-2xl bg-gradient-to-b from-border to-transparent opacity-80"
              />
              <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-[0_24px_80px_-32px_rgba(15,23,42,0.45)]">
                <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="size-2.5 rounded-full bg-border" />
                  <span className="ml-3 text-[11px] text-muted-foreground">
                    Workspace · Ask
                  </span>
                </div>
                <div className="grid text-left sm:grid-cols-[0.9fr_1.1fr]">
                  <div className="hidden border-r border-border p-5 sm:block">
                    <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                      Document
                    </p>
                    <p className="mt-2 text-sm font-medium text-foreground">
                      Office_Lease_2024.pdf
                    </p>
                    <div className="mt-4 space-y-2">
                      {[72, 90, 64, 80, 56].map((w, i) => (
                        <div
                          key={i}
                          className="h-2 rounded-full bg-muted"
                          style={{ width: `${w}%` }}
                        />
                      ))}
                    </div>
                  </div>
                  <div className="space-y-4 p-5 sm:p-6">
                    <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-foreground px-3.5 py-2.5 text-sm text-background">
                      Can either party terminate after year one?
                    </div>
                    <div className="max-w-[95%] rounded-2xl rounded-bl-md border border-border bg-muted/30 px-3.5 py-3 text-sm leading-relaxed text-foreground">
                      Yes — after the first year, either party may terminate with{" "}
                      <span className="rounded bg-primary/15 px-1 font-medium">
                        30 days’ written notice
                      </span>
                      , per Section 8.2.
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
                          Lease.pdf · p.4
                        </span>
                        <span className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] text-muted-foreground">
                          Confidence High
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>
        </section>

        <section className="border-t border-border">
          <div className="mx-auto grid max-w-5xl gap-0 px-5 sm:grid-cols-3 sm:px-8">
            {[
              {
                n: "01",
                t: "Upload",
                d: "Contracts, leases, NDAs — private to your account.",
              },
              {
                n: "02",
                t: "Ask with evidence",
                d: "Plain-language answers grounded in citations you can open.",
              },
              {
                n: "03",
                t: "Act with judgment",
                d: "Risks, briefings, and a path to the right professional.",
              },
            ].map((s, i) => (
              <div
                key={s.n}
                className={`py-12 sm:py-14 ${i > 0 ? "border-t border-border sm:border-t-0 sm:border-l sm:pl-8" : "sm:pr-8"}`}
              >
                <p className="font-mono text-[11px] text-muted-foreground">{s.n}</p>
                <h2 className="mt-3 text-lg font-semibold tracking-tight text-foreground">
                  {s.t}
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.d}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-5xl flex-col gap-3 px-5 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p>© {new Date().getFullYear()} Legal Copilot</p>
          <div className="flex gap-5">
            <a
              href="/account/disclaimer"
              className="hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Disclaimer
            </a>
            <a
              href="/account/privacy"
              className="hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Privacy
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
