"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsDeleteView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsDeleteView />
    </RequireAuth>
  );
}
