"use client";

import { Suspense } from "react";
import { VerifyEmailView } from "@/components/auth/verify-email-view";
import { AuthPageLoader } from "@/components/auth/auth-feedback";

export default function VerifyPage() {
  return (
    <Suspense fallback={<AuthPageLoader />}>
      <VerifyEmailView />
    </Suspense>
  );
}
