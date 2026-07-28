"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsNotificationsView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsNotificationsView />
    </RequireAuth>
  );
}
