"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsPasswordView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsPasswordView />
    </RequireAuth>
  );
}
