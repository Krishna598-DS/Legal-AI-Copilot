"use client";

import { Suspense } from "react";
import { GuestOnly } from "@/components/layout/guest-only";
import { SignInView } from "@/components/auth/sign-in-view";
import { AuthPageLoader } from "@/components/auth/auth-feedback";

export default function SignInPage() {
  return (
    <GuestOnly>
      <Suspense fallback={<AuthPageLoader />}>
        <SignInView />
      </Suspense>
    </GuestOnly>
  );
}
