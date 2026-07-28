"use client";

import { GuestOnly } from "@/components/layout/guest-only";
import { ForgotPasswordView } from "@/components/auth/forgot-password-view";

export default function ForgotPage() {
  return (
    <GuestOnly>
      <ForgotPasswordView />
    </GuestOnly>
  );
}
