"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Bell, CheckCircle2, AlertTriangle, Loader2, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAuth } from "@/components/providers/auth-provider";
import { routes } from "@/lib/routes";
import type { WorkspaceNotification } from "@/lib/types";
import {
  dismissNotif,
  isFailed,
  isProcessing,
  isReady,
  markReadySeen,
  readDismissedNotifs,
  readSeenReadyIds,
  relativeTime,
} from "@/lib/workspace-activity";
import { readNotificationPrefs } from "@/lib/settings-prefs";
import { cn } from "@/lib/utils";

function buildNotifications(
  docs: ReturnType<typeof useAuth>["docs"],
  emailVerified?: boolean
): WorkspaceNotification[] {
  const dismissed = readDismissedNotifs();
  const prefs = readNotificationPrefs();
  const items: WorkspaceNotification[] = [];

  if (emailVerified === false && prefs.emailVerifyReminders) {
    items.push({
      id: "verify-email",
      kind: "verify",
      title: "Verify your email",
      body: "Confirm your address to keep account recovery available.",
      href: routes.settingsSecurity,
    });
  }

  docs.forEach((d) => {
    if (isProcessing(d.status)) {
      items.push({
        id: `processing-${d.id}`,
        kind: "processing",
        title: "Processing document",
        body: d.original_filename,
        href: routes.documents,
        at: d.created_at,
      });
    } else if (isFailed(d.status)) {
      if (!prefs.documentFailed) return;
      items.push({
        id: `failed-${d.id}`,
        kind: "failed",
        title: "Processing failed",
        body: d.processing_error || d.original_filename,
        href: routes.documents,
        at: d.created_at,
      });
    } else if (isReady(d.status)) {
      if (!prefs.documentReady) return;
      // Only surface freshly ready docs — older READY items already live in
      // Recent documents / Continue, and would drown the tray on every login.
      const created = d.created_at ? new Date(d.created_at).getTime() : 0;
      const fresh = created > 0 && Date.now() - created < 2 * 60 * 60 * 1000;
      if (!fresh) return;
      items.push({
        id: `ready-${d.id}`,
        kind: "ready",
        title: "Document ready",
        body: `${d.original_filename} is ready to review`,
        href: routes.workspace(d.id, "ask"),
        at: d.created_at,
      });
    }
  });

  // Only surface "ready" briefly: hide after user has opened the tray once
  // for that document (still show processing/failed until dismissed).
  const seenReady = readSeenReadyIds();
  return items.filter((n) => {
    if (dismissed.has(n.id)) return false;
    if (n.kind === "ready" && seenReady.has(n.id.replace(/^ready-/, ""))) {
      return false;
    }
    return true;
  });
}

const kindIcon = {
  processing: Loader2,
  ready: CheckCircle2,
  failed: AlertTriangle,
  verify: Mail,
  info: Bell,
} as const;

export function NotificationsMenu() {
  const { docs, user } = useAuth();
  const [open, setOpen] = useState(false);
  const [tick, setTick] = useState(0);

  const notifications = useMemo(
    () => buildNotifications(docs, user?.email_verified),
    // tick forces refresh after dismiss
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [docs, user?.email_verified, tick]
  );

  const unread = notifications.length;

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (!next) {
      // Mark ready docs as seen when closing the tray so the badge clears,
      // but only after the user had a chance to read them.
      const readyIds = docs.filter((d) => isReady(d.status)).map((d) => d.id);
      markReadySeen(readyIds);
      setTick((t) => t + 1);
    }
  }

  function onDismiss(id: string) {
    dismissNotif(id);
    setTick((t) => t + 1);
  }

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label={unread ? `${unread} notifications` : "Notifications"}
        >
          <Bell className="size-4" />
          {unread > 0 ? (
            <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-primary" />
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[360px] p-0">
        <div className="flex items-center justify-between border-b border-border px-3 py-2.5">
          <p className="text-sm font-semibold">Notifications</p>
          {unread ? (
            <span className="text-xs text-muted-foreground">{unread} open</span>
          ) : null}
        </div>
        {!notifications.length ? (
          <p className="px-4 py-10 text-center text-sm text-muted-foreground">
            You&apos;re caught up. Processing updates and document status will
            appear here.
          </p>
        ) : (
          <ul className="max-h-[360px] divide-y divide-border overflow-y-auto">
            {notifications.map((n) => {
              const Icon = kindIcon[n.kind];
              return (
                <li key={n.id} className="group relative">
                  <Link
                    href={n.href || routes.home}
                    onClick={() => {
                      onDismiss(n.id);
                      setOpen(false);
                    }}
                    className="flex gap-3 px-3 py-3 transition-colors hover:bg-muted/60"
                  >
                    <Icon
                      className={cn(
                        "mt-0.5 size-4 shrink-0",
                        n.kind === "failed" && "text-destructive",
                        n.kind === "ready" && "text-success",
                        n.kind === "processing" && "animate-spin text-warning",
                        n.kind === "verify" && "text-primary"
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-foreground">
                        {n.title}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-muted-foreground">
                        {n.body}
                      </p>
                      {n.at ? (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          {relativeTime(n.at)}
                        </p>
                      ) : null}
                    </div>
                  </Link>
                  <button
                    type="button"
                    className="absolute right-2 top-2 hidden rounded px-1.5 text-[11px] text-muted-foreground hover:bg-muted group-hover:inline"
                    onClick={() => onDismiss(n.id)}
                  >
                    Dismiss
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
