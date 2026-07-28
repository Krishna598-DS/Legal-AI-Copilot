"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { AdminView } from "@/components/admin/admin-view";

export default function AdminPage() {
  return (
    <RequireAuth>
      <AdminView />
    </RequireAuth>
  );
}
