"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

export type SidebarLink = {
  href: string;
  label: string;
  icon?: React.ReactNode;
};

export function AppSidebar({
  title = "AI Legal Copilot",
  groups,
  footer,
}: {
  title?: string;
  groups: { label?: string; items: SidebarLink[] }[];
  footer?: React.ReactNode;
}) {
  const pathname = usePathname() || "/";

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <SidebarTrigger className="-ml-1" />
          <span className="font-display truncate text-sm font-bold">{title}</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {groups.map((group, gi) => (
          <SidebarGroup key={group.label ?? gi}>
            {group.label ? <SidebarGroupLabel>{group.label}</SidebarGroupLabel> : null}
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const active =
                    pathname === item.href ||
                    pathname.startsWith(item.href.replace(/\/$/, ""));
                  return (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton asChild isActive={active} tooltip={item.label}>
                        <Link href={item.href}>
                          {item.icon}
                          <span>{item.label}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  );
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      {footer ? (
        <>
          <SidebarSeparator />
          <SidebarFooter>{footer}</SidebarFooter>
        </>
      ) : null}
      <SidebarRail />
    </Sidebar>
  );
}

export function AppShellFrame({
  sidebar,
  children,
  className,
}: {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <>
      {sidebar}
      <SidebarInset className={cn(className)}>{children}</SidebarInset>
    </>
  );
}
