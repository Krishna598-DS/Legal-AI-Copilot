"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsSecurityView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsSecurityView />
    </RequireAuth>
  );
}
