"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsSessionsView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsSessionsView />
    </RequireAuth>
  );
}
