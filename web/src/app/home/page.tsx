"use client";

import { RequireAuth } from "@/components/layout/require-auth";
import { HomeView } from "@/components/home/home-view";

export default function HomePage() {
  return (
    <RequireAuth>
      <HomeView />
    </RequireAuth>
  );
}
