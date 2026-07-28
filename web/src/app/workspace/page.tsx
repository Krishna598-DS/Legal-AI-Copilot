"use client";

import { Suspense } from "react";
import { RequireAuth } from "@/components/layout/require-auth";
import { LoadingBlock, PageShell } from "@/components/ui/page-shell";
import { WorkspaceView } from "@/components/workspace/workspace-view";

export default function WorkspacePage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <PageShell>
            <LoadingBlock label="Loading workspace…" />
          </PageShell>
        }
      >
        <WorkspaceView />
      </Suspense>
    </RequireAuth>
  );
}
