"use client";

import { Suspense } from "react";
import { CheckEmailView } from "@/components/auth/check-email-view";
import { AuthPageLoader } from "@/components/auth/auth-feedback";

export default function CheckEmailPage() {
  return (
    <Suspense fallback={<AuthPageLoader />}>
      <CheckEmailView />
    </Suspense>
  );
}
