"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsAccountView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsAccountView />
    </RequireAuth>
  );
}
