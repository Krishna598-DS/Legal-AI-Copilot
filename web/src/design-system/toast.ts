"use client";

import { toast as sonnerToast } from "sonner";

/** Typed toast helpers — use everywhere instead of ad-hoc alerts. */
export const toast = {
  success: (message: string, description?: string) =>
    sonnerToast.success(message, { description }),
  error: (message: string, description?: string) =>
    sonnerToast.error(message, { description }),
  info: (message: string, description?: string) =>
    sonnerToast.message(message, { description }),
  warning: (message: string, description?: string) =>
    sonnerToast.warning(message, { description }),
  promise: sonnerToast.promise,
  dismiss: sonnerToast.dismiss,
};
