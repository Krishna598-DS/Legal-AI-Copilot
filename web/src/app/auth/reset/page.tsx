"use client";

import { Suspense } from "react";
import { GuestOnly } from "@/components/layout/guest-only";
import { ResetPasswordView } from "@/components/auth/reset-password-view";
import { AuthPageLoader } from "@/components/auth/auth-feedback";

export default function ResetPage() {
  return (
    <GuestOnly>
      <Suspense fallback={<AuthPageLoader />}>
        <ResetPasswordView />
      </Suspense>
    </GuestOnly>
  );
}
