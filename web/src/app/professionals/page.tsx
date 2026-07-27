"use client";

import { Suspense } from "react";
import { RequireAuth } from "@/components/layout/require-auth";
import { LoadingBlock, PageShell } from "@/components/ui/page-shell";
import { ProfessionalsView } from "@/components/professionals/professionals-view";

export default function ProfessionalsPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <PageShell className="max-w-4xl">
            <LoadingBlock label="Loading directory…" />
          </PageShell>
        }
      >
        <ProfessionalsView />
      </Suspense>
    </RequireAuth>
  );
}
