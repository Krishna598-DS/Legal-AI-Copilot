"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsProfileView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsProfileView />
    </RequireAuth>
  );
}
