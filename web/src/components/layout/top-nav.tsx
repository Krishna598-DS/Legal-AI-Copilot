"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { BrandMark } from "@/components/brand/brand-mark";
import {
  CommandSearch,
  useCommandSearchShortcut,
} from "@/components/home/command-search";
import { NotificationsMenu } from "@/components/home/notifications-menu";
import { Button } from "@/components/ui/button";
import { UserMenu } from "@/design-system";
import { OPEN_SEARCH_EVENT } from "@/lib/open-search";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const NAV = [
  {
    href: routes.home,
    label: "Home",
    match: (p: string) => p === "/home" || p.startsWith("/home/"),
  },
  {
    href: routes.documents,
    label: "Documents",
    match: (p: string) => p.startsWith("/documents") || p.startsWith("/workspace"),
  },
  {
    href: routes.professionals(),
    label: "Directory",
    match: (p: string) => p.startsWith("/professionals"),
  },
];

export function TopNav() {
  const pathname = usePathname() || "/";
  const router = useRouter();
  const { user, isAdmin, logout } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const openSearch = useCallback(() => setSearchOpen(true), []);
  useCommandSearchShortcut(openSearch);

  useEffect(() => {
    function onOpen() {
      setSearchOpen(true);
    }
    window.addEventListener(OPEN_SEARCH_EVENT, onOpen);
    return () => window.removeEventListener(OPEN_SEARCH_EVENT, onOpen);
  }, []);

  return (
    <>
      <CommandSearch open={searchOpen} onOpenChange={setSearchOpen} />
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-6">
            <BrandMark href={routes.home} />
            <nav aria-label="Primary" className="hidden items-center gap-0.5 md:flex">
              {NAV.map((item) => {
                const active = item.match(pathname);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "relative rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      active
                        ? "text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {item.label}
                    {active ? (
                      <span
                        aria-hidden
                        className="absolute inset-x-3 -bottom-[0.95rem] h-px bg-foreground"
                      />
                    ) : null}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="hidden h-8 gap-2 text-muted-foreground md:inline-flex"
              onClick={openSearch}
            >
              <Search className="size-3.5" />
              <span className="text-[13px]">Search</span>
              <kbd className="ml-1 rounded border border-border bg-muted/60 px-1.5 py-0.5 font-sans text-[10px] text-muted-foreground">
                ⌘K
              </kbd>
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              aria-label="Search"
              onClick={openSearch}
            >
              <Search className="size-4" />
            </Button>
            <NotificationsMenu />
            {isAdmin ? (
              <Button
                size="sm"
                variant="ghost"
                className="hidden h-8 text-[13px] text-muted-foreground sm:inline-flex"
                onClick={() => router.push(routes.admin)}
              >
                Admin
              </Button>
            ) : null}
            <UserMenu
              email={user?.email}
              name={user?.full_name}
              settingsHref={routes.settingsProfile}
              onSignOut={async () => {
                await logout();
                router.push(routes.signIn);
              }}
            />
          </div>
        </div>

        <nav
          className="flex gap-1 overflow-x-auto border-t border-border/60 px-4 py-1 md:hidden scrollbar-none"
          aria-label="Primary mobile"
        >
          {NAV.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "shrink-0 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
    </>
  );
}
