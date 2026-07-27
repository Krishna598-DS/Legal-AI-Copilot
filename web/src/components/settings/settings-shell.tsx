"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  type LucideIcon,
  Bell,
  KeyRound,
  Lock,
  MonitorSmartphone,
  Palette,
  Plug,
  Shield,
  Trash2,
  UserRound,
  WalletCards,
  Fingerprint,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { routes } from "@/lib/routes";

export type FormStatusState =
  | { kind: "idle" }
  | { kind: "loading"; message?: string }
  | { kind: "success"; message: string }
  | { kind: "error"; message: string };

export const IDLE: FormStatusState = { kind: "idle" };

type NavItem = {
  href: string;
  label: string;
  description: string;
  icon: LucideIcon;
  group: "Personal" | "Security" | "Developer" | "Account";
};

export const SETTINGS_NAV: NavItem[] = [
  {
    href: routes.settingsProfile,
    label: "Profile",
    description: "Name and persona",
    icon: UserRound,
    group: "Personal",
  },
  {
    href: routes.settingsNotifications,
    label: "Notifications",
    description: "Alerts and reminders",
    icon: Bell,
    group: "Personal",
  },
  {
    href: routes.settingsTheme,
    label: "Theme",
    description: "Light or dark",
    icon: Palette,
    group: "Personal",
  },
  {
    href: routes.settingsSecurity,
    label: "Security",
    description: "Email and account safety",
    icon: Shield,
    group: "Security",
  },
  {
    href: routes.settingsPassword,
    label: "Password",
    description: "Change your password",
    icon: Lock,
    group: "Security",
  },
  {
    href: routes.settingsSessions,
    label: "Sessions",
    description: "Active sign-ins",
    icon: Fingerprint,
    group: "Security",
  },
  {
    href: routes.settingsDevices,
    label: "Devices",
    description: "Browsers you use",
    icon: MonitorSmartphone,
    group: "Security",
  },
  {
    href: routes.settingsApiKeys,
    label: "API Keys",
    description: "Personal access keys",
    icon: KeyRound,
    group: "Developer",
  },
  {
    href: routes.settingsMcp,
    label: "MCP",
    description: "Connect AI clients",
    icon: Plug,
    group: "Developer",
  },
  {
    href: routes.settingsAccount,
    label: "Account",
    description: "Plan and usage",
    icon: WalletCards,
    group: "Account",
  },
  {
    href: routes.settingsDelete,
    label: "Delete account",
    description: "Close permanently",
    icon: Trash2,
    group: "Account",
  },
];

function pathActive(pathname: string, href: string) {
  const base = href.replace(/\/$/, "");
  return pathname === href || pathname === base || pathname.startsWith(base + "/");
}

export function SettingsNav({ className }: { className?: string }) {
  const pathname = usePathname() || "";
  const groups = ["Personal", "Security", "Developer", "Account"] as const;

  return (
    <nav
      className={cn("space-y-5", className)}
      aria-label="Settings sections"
    >
      {groups.map((group) => (
        <div key={group}>
          <p className="mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {group}
          </p>
          <ul className="space-y-0.5">
            {SETTINGS_NAV.filter((i) => i.group === group).map((item) => {
              const Icon = item.icon;
              const active = pathActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    title={item.description}
                    className={cn(
                      "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 transition-colors",
                      active
                        ? "bg-foreground text-background"
                        : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
                    )}
                  >
                    <Icon
                      className={cn(
                        "size-4 shrink-0",
                        active
                          ? "text-background"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                      aria-hidden
                    />
                    <span className="text-[13px] font-medium leading-none">
                      {item.label}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export function SettingsShell({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      <header className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Settings
        </p>
        <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          {title}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          {description}
        </p>
      </header>

      <div className="flex flex-col gap-8 lg:flex-row lg:gap-10">
        <aside className="lg:w-56 lg:shrink-0">
          <div className="lg:sticky lg:top-20">
            <div className="mb-3 overflow-x-auto lg:hidden">
              <div className="flex gap-1 pb-1" role="tablist" aria-label="Settings">
                {SETTINGS_NAV.map((item) => (
                  <MobileNavChip key={item.href} href={item.href} label={item.label} />
                ))}
              </div>
            </div>
            <div className="hidden lg:block">
              <SettingsNav />
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1 space-y-6">{children}</div>
      </div>
    </div>
  );
}

function MobileNavChip({ href, label }: { href: string; label: string }) {
  const pathname = usePathname() || "";
  const active = pathActive(pathname, href);
  return (
    <Link
      href={href}
      className={cn(
        "shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        active
          ? "border-primary/40 bg-primary/10 text-foreground"
          : "border-border text-muted-foreground hover:text-foreground"
      )}
    >
      {label}
    </Link>
  );
}

export function SettingCard({
  title,
  description,
  children,
  danger,
  className,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  danger?: boolean;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border bg-card p-5 shadow-sm sm:p-6",
        danger ? "border-destructive/35" : "border-border",
        className
      )}
      aria-labelledby={undefined}
    >
      <div className="mb-5 max-w-2xl">
        <h2
          className={cn(
            "text-base font-semibold tracking-tight",
            danger ? "text-destructive" : "text-foreground"
          )}
        >
          {title}
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>
      {children}
    </section>
  );
}

export function FormStatus({ status }: { status: FormStatusState }) {
  if (status.kind === "idle") return null;

  if (status.kind === "loading") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-sm text-muted-foreground"
      >
        <Loader2 className="size-4 animate-spin" aria-hidden />
        {status.message || "Saving…"}
      </div>
    );
  }

  if (status.kind === "success") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-foreground"
      >
        <CheckCircle2 className="size-4 text-success" aria-hidden />
        {status.message}
      </div>
    );
  }

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="flex items-center gap-2 rounded-lg border border-destructive/35 bg-destructive/10 px-3 py-2 text-sm text-destructive"
    >
      <AlertCircle className="size-4 shrink-0" aria-hidden />
      {status.message}
    </div>
  );
}
