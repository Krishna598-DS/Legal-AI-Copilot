"use client";

import { GuestOnly } from "@/components/layout/guest-only";
import { SignUpView } from "@/components/auth/sign-up-view";

export default function SignUpPage() {
  return (
    <GuestOnly>
      <SignUpView />
    </GuestOnly>
  );
}
