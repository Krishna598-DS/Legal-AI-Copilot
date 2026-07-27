"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsApiKeysView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsApiKeysView />
    </RequireAuth>
  );
}
