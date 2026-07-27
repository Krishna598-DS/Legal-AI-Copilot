"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { DocumentsView } from "@/components/documents/documents-view";

export default function DocumentsPage() {
  return (
    <RequireAuth>
      <DocumentsView />
    </RequireAuth>
  );
}
