"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  FileText,
  Loader2,
  MessageSquare,
  Search,
  Sparkles,
  Upload,
  AlertTriangle,
} from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { DisclaimerCallout } from "@/components/patterns/disclaimer-callout";
import { Button } from "@/components/ui/button";
import { FadeIn, EmptyState, EmptyStateAction, StatusBadge } from "@/design-system";
import { PageShell } from "@/components/ui/page-shell";
import { api } from "@/lib/api";
import { personaActions } from "@/lib/dashboard-actions";
import { runAction } from "@/lib/action-destinations";
import { openWorkspaceSearch } from "@/lib/open-search";
import { routes, type WorkspaceMode } from "@/lib/routes";
import type { ChatMessage, DocumentRow, RecentConversation } from "@/lib/types";
import {
  isFailed,
  isProcessing,
  readLastWorkspace,
  relativeTime,
  type LastWorkspace,
} from "@/lib/workspace-activity";

const QUICK = [
  { id: "upload", label: "Upload", icon: Upload, href: routes.documents },
  { id: "ask", label: "Ask", icon: MessageSquare, mode: "ask" as WorkspaceMode },
  { id: "explain", label: "Explain", icon: Sparkles, mode: "explain" as WorkspaceMode },
  { id: "risks", label: "Risks", icon: AlertTriangle, mode: "risks" as WorkspaceMode },
] as const;

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function SectionHeader({
  title,
  href,
  linkLabel,
}: {
  title: string;
  href?: string;
  linkLabel?: string;
}) {
  return (
    <div className="mb-3 flex items-baseline justify-between gap-3">
      <h2 className="text-sm font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      {href ? (
        <Link
          href={href}
          className="text-xs font-medium text-muted-foreground transition-colors hover:text-primary"
        >
          {linkLabel || "View all"}
        </Link>
      ) : null}
    </div>
  );
}

function RowLink({
  href,
  title,
  meta,
  trailing,
  icon,
}: {
  href: string;
  title: string;
  meta?: string;
  trailing?: React.ReactNode;
  icon?: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-muted/70"
    >
      {icon ? (
        <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-background text-muted-foreground">
          {icon}
        </span>
      ) : null}
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground group-hover:text-primary">
          {title}
        </span>
        {meta ? (
          <span className="mt-0.5 block truncate text-xs text-muted-foreground">
            {meta}
          </span>
        ) : null}
      </span>
      {trailing}
      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </Link>
  );
}

export function HomeView() {
  const { user, token, docs, readyDocs, refreshDocs } = useAuth();
  const router = useRouter();
  const [last, setLast] = useState<LastWorkspace | null>(null);
  const [conversations, setConversations] = useState<RecentConversation[]>([]);
  const [loadingChats, setLoadingChats] = useState(false);

  const latestReadyId = readyDocs[0]?.id || null;
  const processing = useMemo(() => docs.filter((d) => isProcessing(d.status)), [docs]);
  const failed = useMemo(() => docs.filter((d) => isFailed(d.status)), [docs]);
  const recentDocs = useMemo(() => docs.slice(0, 6), [docs]);

  const continueTarget = useMemo(() => {
    if (last) {
      const stillThere = docs.find((d) => d.id === last.documentId);
      if (stillThere) {
        return {
          ...last,
          filename: stillThere.original_filename || last.filename,
          status: stillThere.status,
        };
      }
    }
    if (readyDocs[0]) {
      return {
        documentId: readyDocs[0].id,
        filename: readyDocs[0].original_filename,
        mode: "ask" as WorkspaceMode,
        at: readyDocs[0].created_at || new Date().toISOString(),
        status: readyDocs[0].status,
      };
    }
    return null;
  }, [docs, last, readyDocs]);

  const suggestions = useMemo(() => {
    const actions = personaActions(user?.role);
    if (!docs.length) {
      return actions.filter((a) => a.id === "upload" || a.id === "explain").slice(0, 3);
    }
    if (processing.length && !readyDocs.length) {
      return [
        {
          id: "wait",
          kicker: "In progress",
          title: "Check processing status",
          desc: "Your document is being indexed. You’ll be able to ask once it’s ready.",
          go: "View documents",
        },
        ...actions.filter((a) => a.id === "upload").slice(0, 1),
      ];
    }
    if (readyDocs.length && !conversations.length) {
      return actions
        .filter((a) => ["explain", "ask", "risks"].includes(a.id))
        .slice(0, 3);
    }
    return actions
      .filter((a) => a.id !== "upload")
      .slice(0, 3);
  }, [conversations.length, docs.length, processing.length, readyDocs.length, user?.role]);

  useEffect(() => {
    setLast(readLastWorkspace());
  }, []);

  // Poll while documents are processing
  useEffect(() => {
    if (!processing.length) return;
    const id = window.setInterval(() => {
      refreshDocs().catch(() => {});
    }, 2500);
    return () => window.clearInterval(id);
  }, [processing.length, refreshDocs]);

  // Load recent conversations from message history
  useEffect(() => {
    if (!token || !readyDocs.length) {
      setConversations([]);
      return;
    }
    let cancelled = false;
    setLoadingChats(true);
    (async () => {
      const sample = readyDocs.slice(0, 8);
      const results = await Promise.all(
        sample.map(async (d) => {
          try {
            const messages = await api<ChatMessage[]>(
              `/documents/${d.id}/messages`,
              { token, timeoutMs: 8000 }
            );
            const users = messages.filter((m) => m.role === "user");
            if (!users.length) return null;
            const lastUser = users[users.length - 1];
            const at =
              lastUser.created_at ||
              messages[messages.length - 1]?.created_at ||
              d.created_at ||
              new Date(0).toISOString();
            return {
              documentId: d.id,
              filename: d.original_filename,
              preview: lastUser.content.trim().slice(0, 120),
              at,
              messageCount: messages.length,
            } satisfies RecentConversation;
          } catch {
            return null;
          }
        })
      );
      if (cancelled) return;
      const list = results
        .filter((r): r is RecentConversation => Boolean(r))
        .sort((a, b) => new Date(b.at).getTime() - new Date(a.at).getTime())
        .slice(0, 5);
      setConversations(list);
      setLoadingChats(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [token, readyDocs]);

  const firstName = user?.full_name?.trim()?.split(/\s+/)[0];

  return (
    <PageShell>
      <FadeIn>
        <header className="mb-10">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl font-bold tracking-tight text-foreground md:text-[2.5rem] md:leading-tight">
                {greeting()}
                {firstName ? `, ${firstName}` : ""}
              </h1>
              <p className="mt-2 max-w-lg text-[15px] text-muted-foreground">
                Continue a document, or start something new.
              </p>
            </div>
            <Button variant="primary" onClick={() => router.push(routes.documents)}>
              <Upload className="size-4" />
              Upload
            </Button>
          </div>

          <button
            type="button"
            onClick={openWorkspaceSearch}
            className="mt-6 flex w-full items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left text-[13px] text-muted-foreground shadow-sm transition-colors hover:border-foreground/20 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <Search className="size-4 shrink-0" />
            <span className="flex-1">Search documents and conversations</span>
            <kbd className="hidden rounded-md border border-border bg-muted/50 px-1.5 py-0.5 text-[10px] font-medium sm:inline">
              ⌘K
            </kbd>
          </button>
        </header>
      </FadeIn>

      {!docs.length ? (
        <FadeIn delay={0.05}>
          <EmptyState
            className="mb-8 border-border bg-card"
            icon={<FileText className="size-8" />}
            title="Your workspace is ready"
            description="Upload a contract or agreement to ask cited questions, explain clauses, and prepare for consultations."
            action={
              <EmptyStateAction onClick={() => router.push(routes.documents)}>
                Upload your first document
              </EmptyStateAction>
            }
          />
        </FadeIn>
      ) : null}

      {continueTarget ? (
        <FadeIn delay={0.04}>
          <section className="mb-8">
            <SectionHeader title="Continue where you left off" />
            <Link
              href={routes.workspace(continueTarget.documentId, continueTarget.mode)}
              className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-sm transition-colors hover:border-primary/40 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {continueTarget.mode === "ask"
                    ? "Conversation"
                    : continueTarget.mode.charAt(0).toUpperCase() +
                      continueTarget.mode.slice(1)}
                </p>
                <p className="mt-1 truncate text-base font-semibold text-foreground group-hover:text-primary">
                  {continueTarget.filename}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Last opened {relativeTime(continueTarget.at) || "recently"}
                </p>
              </div>
              <span className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                Resume
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          </section>
        </FadeIn>
      ) : null}

      {(processing.length > 0 || failed.length > 0) && (
        <FadeIn delay={0.06}>
          <section className="mb-8">
            <SectionHeader
              title="Needs attention"
              href={routes.documents}
              linkLabel="Documents"
            />
            <ul className="divide-y divide-border rounded-xl border border-border bg-card">
              {processing.map((d) => (
                <li key={d.id}>
                  <RowLink
                    href={routes.documents}
                    title={d.original_filename}
                    meta="Indexing for cited answers…"
                    icon={<Loader2 className="size-4 animate-spin" />}
                    trailing={<StatusBadge status={d.status} />}
                  />
                </li>
              ))}
              {failed.map((d) => (
                <li key={d.id}>
                  <RowLink
                    href={routes.documents}
                    title={d.original_filename}
                    meta={d.processing_error || "Processing failed — retry from Documents"}
                    icon={<AlertTriangle className="size-4 text-destructive" />}
                    trailing={<StatusBadge status={d.status} />}
                  />
                </li>
              ))}
            </ul>
          </section>
        </FadeIn>
      )}

      <div className="grid gap-8 lg:grid-cols-[1fr_300px]">
        <div className="space-y-8">
          <FadeIn delay={0.08}>
            <section>
              <SectionHeader title="Recent conversations" />
              {loadingChats ? (
                <div className="rounded-xl border border-border bg-card px-4 py-8 text-center text-sm text-muted-foreground">
                  Loading conversations…
                </div>
              ) : !conversations.length ? (
                <div className="rounded-xl border border-dashed border-border bg-muted/20 px-4 py-8 text-center">
                  <p className="text-sm text-muted-foreground">
                    {readyDocs.length
                      ? "No conversations yet. Ask a question on a ready document."
                      : "Conversations will appear after you upload and ask."}
                  </p>
                  {latestReadyId ? (
                    <Button
                      className="mt-3"
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        router.push(routes.workspace(latestReadyId, "ask"))
                      }
                    >
                      Start asking
                    </Button>
                  ) : null}
                </div>
              ) : (
                <ul className="divide-y divide-border rounded-xl border border-border bg-card">
                  {conversations.map((c) => (
                    <li key={c.documentId}>
                      <RowLink
                        href={routes.workspace(c.documentId, "ask")}
                        title={c.preview}
                        meta={`${c.filename} · ${relativeTime(c.at)} · ${c.messageCount} messages`}
                        icon={<MessageSquare className="size-4" />}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </FadeIn>

          <FadeIn delay={0.1}>
            <section>
              <SectionHeader
                title="Recent documents"
                href={routes.documents}
                linkLabel="All documents"
              />
              {!recentDocs.length ? (
                <div className="rounded-xl border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  No documents yet.
                </div>
              ) : (
                <ul className="divide-y divide-border rounded-xl border border-border bg-card">
                  {recentDocs.map((d: DocumentRow) => (
                    <li key={d.id}>
                      <RowLink
                        href={routes.workspace(d.id, "ask")}
                        title={d.original_filename}
                        meta={relativeTime(d.created_at) || undefined}
                        icon={<FileText className="size-4" />}
                        trailing={<StatusBadge status={d.status} />}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </FadeIn>
        </div>

        <aside className="space-y-6">
          <FadeIn delay={0.08}>
            <section>
              <SectionHeader title="Shortcuts" />
              <div className="flex flex-wrap gap-2">
                {QUICK.map((q) => {
                  const Icon = q.icon;
                  const href =
                    q.id === "upload"
                      ? routes.documents
                      : latestReadyId
                        ? routes.workspace(latestReadyId, q.mode!)
                        : routes.documents;
                  return (
                    <button
                      key={q.id}
                      type="button"
                      onClick={() => router.push(href)}
                      className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <Icon className="size-3.5 text-muted-foreground" />
                      {q.label}
                    </button>
                  );
                })}
              </div>
            </section>
          </FadeIn>

          {suggestions.length ? (
            <FadeIn delay={0.1}>
              <section>
                <SectionHeader title="Next step" />
                <button
                  type="button"
                  onClick={() => {
                    const action = suggestions[0];
                    if (!action) return;
                    if (action.id === "wait") {
                      router.push(routes.documents);
                      return;
                    }
                    runAction(action, latestReadyId, (href) => router.push(href));
                  }}
                  className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-foreground/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                    {suggestions[0]?.kicker}
                  </p>
                  <p className="mt-1.5 text-sm font-semibold text-foreground">
                    {suggestions[0]?.title}
                  </p>
                  <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
                    {suggestions[0]?.desc}
                  </p>
                </button>
              </section>
            </FadeIn>
          ) : null}

          <FadeIn delay={0.12}>
            <DisclaimerCallout />
          </FadeIn>
        </aside>
      </div>
    </PageShell>
  );
}
