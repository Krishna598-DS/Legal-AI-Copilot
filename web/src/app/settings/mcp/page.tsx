"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { SettingsMcpView } from "@/components/settings/settings-views";

export default function Page() {
  return (
    <RequireAuth>
      <SettingsMcpView />
    </RequireAuth>
  );
}
