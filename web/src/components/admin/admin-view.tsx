"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import {
  LoadingBlock,
  PageShell,
  SegmentedTabs,
  StatusBanner,
  SurfaceCard,
} from "@/components/ui/page-shell";
import { EmptyState, PageHeader } from "@/design-system";
import { api } from "@/lib/api";
import { toast } from "@/design-system/toast";

type AdminUser = {
  id: string;
  email: string;
  full_name?: string;
  is_active?: boolean;
};

type AdminPro = {
  id: string;
  name: string;
  specialization?: string;
  city?: string;
  verified?: boolean;
};

export function AdminView() {
  const { token, isAdmin } = useAuth();
  const [tab, setTab] = useState<"overview" | "users" | "professionals">(
    "overview"
  );
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [pros, setPros] = useState<AdminPro[]>([]);
  const [error, setError] = useState("");
  const [loadingStats, setLoadingStats] = useState(false);
  const [loadingList, setLoadingList] = useState(false);

  useEffect(() => {
    if (!token || !isAdmin) return;
    void (async () => {
      setLoadingStats(true);
      try {
        const s = await api<Record<string, unknown>>("/admin/stats", { token });
        setStats(s);
        setError("");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load admin");
      } finally {
        setLoadingStats(false);
      }
    })();
  }, [token, isAdmin]);

  async function loadUsers() {
    if (!token) return;
    setLoadingList(true);
    try {
      const list = await api<AdminUser[]>("/admin/users", { token });
      setUsers(list || []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoadingList(false);
    }
  }

  async function loadPros() {
    if (!token) return;
    setLoadingList(true);
    try {
      const list = await api<AdminPro[]>("/admin/professionals", { token });
      setPros(list || []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load professionals");
    } finally {
      setLoadingList(false);
    }
  }

  if (!isAdmin) {
    return (
      <PageShell className="max-w-lg py-16">
        <EmptyState
          title="Admin access required"
          description="This area is limited to administrators on this deployment."
        />
      </PageShell>
    );
  }

  return (
    <PageShell className="max-w-5xl">
      <PageHeader
        title="Admin"
        description="Operational overview for users and the professional directory."
      />

      <SegmentedTabs
        ariaLabel="Admin sections"
        value={tab}
        onChange={(id) => {
          const next = id as typeof tab;
          setTab(next);
          if (next === "users") void loadUsers();
          if (next === "professionals") void loadPros();
        }}
        items={[
          { id: "overview", label: "Overview" },
          { id: "users", label: "Users" },
          { id: "professionals", label: "Professionals" },
        ]}
      />

      {error ? (
        <div className="mt-4">
          <StatusBanner tone="error">{error}</StatusBanner>
        </div>
      ) : null}

      {tab === "overview" && (
        <div className="mt-6">
          {loadingStats ? (
            <LoadingBlock label="Loading stats…" />
          ) : stats ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(stats).map(([k, v]) => (
                <SurfaceCard key={k} className="hover:shadow-sm">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                    {k.replace(/_/g, " ")}
                  </p>
                  <p className="mt-2 text-xl font-semibold tracking-tight text-foreground">
                    {typeof v === "object" ? JSON.stringify(v) : String(v)}
                  </p>
                </SurfaceCard>
              ))}
            </div>
          ) : (
            <EmptyState title="No stats yet" description="Stats will appear once the admin API responds." />
          )}
        </div>
      )}

      {tab === "users" && (
        <div className="mt-6">
          {loadingList ? (
            <LoadingBlock label="Loading users…" />
          ) : !users.length ? (
            <EmptyState title="No users" description="There are no users to display." />
          ) : (
            <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {users.map((u) => (
                <li
                  key={u.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-muted/30"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-foreground">{u.email}</p>
                    <p className="text-xs text-muted-foreground">
                      {u.full_name || u.id}
                      {u.is_active === false ? " · Disabled" : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={async () => {
                        if (!token) return;
                        try {
                          await api(`/admin/users/${u.id}/disable`, {
                            method: "POST",
                            token,
                          });
                          toast.success("User disabled");
                          await loadUsers();
                        } catch (err) {
                          toast.error(
                            err instanceof Error ? err.message : "Disable failed"
                          );
                        }
                      }}
                    >
                      Disable
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={async () => {
                        if (!token) return;
                        try {
                          await api(`/admin/users/${u.id}/enable`, {
                            method: "POST",
                            token,
                          });
                          toast.success("User enabled");
                          await loadUsers();
                        } catch (err) {
                          toast.error(
                            err instanceof Error ? err.message : "Enable failed"
                          );
                        }
                      }}
                    >
                      Enable
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "professionals" && (
        <div className="mt-6">
          {loadingList ? (
            <LoadingBlock label="Loading professionals…" />
          ) : !pros.length ? (
            <EmptyState
              title="No professionals"
              description="Directory entries will appear here."
            />
          ) : (
            <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card shadow-sm">
              {pros.map((p) => (
                <li
                  key={p.id}
                  className="px-4 py-3 transition-colors hover:bg-muted/30"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium text-foreground">{p.name}</p>
                    {p.verified ? (
                      <span className="rounded-md border border-success/30 bg-success/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide">
                        Verified
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-0.5 text-sm text-muted-foreground">
                    {p.specialization}
                    {p.city ? ` · ${p.city}` : ""}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </PageShell>
  );
}
