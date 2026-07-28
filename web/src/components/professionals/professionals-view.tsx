"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Loader2, MapPin, Search } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import {
  ContactChip,
  LoadingBlock,
  PageShell,
  StatusBanner,
  SurfaceCard,
} from "@/components/ui/page-shell";
import { EmptyState, Input, PageHeader } from "@/design-system";
import { api } from "@/lib/api";
import type { Professional } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ProfessionalsView() {
  const { token } = useAuth();
  const search = useSearchParams();
  const [category, setCategory] = useState(search.get("category") || "");
  const [city, setCity] = useState(search.get("city") || "");
  const [pros, setPros] = useState<Professional[]>([]);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loc, setLoc] = useState<{ latitude: number; longitude: number } | null>(
    null
  );

  async function load(opts?: {
    specialization?: string;
    city?: string;
    latitude?: number;
    longitude?: number;
  }) {
    if (!token) return;
    const params = new URLSearchParams();
    const spec = opts?.specialization ?? category;
    const c = opts?.city ?? city;
    if (spec.trim()) params.set("specialization", spec.trim());
    if (c.trim()) params.set("city", c.trim());
    const latitude = opts?.latitude ?? loc?.latitude;
    const longitude = opts?.longitude ?? loc?.longitude;
    if (latitude != null && longitude != null) {
      params.set("latitude", String(latitude));
      params.set("longitude", String(longitude));
    }
    setLoading(true);
    setError("");
    setStatus("Searching directory…");
    try {
      const list = await api<Professional[]>(
        `/professionals/recommend?${params.toString()}`,
        { token }
      );
      setPros(list || []);
      setStatus(
        list?.length
          ? `${list.length} match${list.length === 1 ? "" : "es"}`
          : "No directory profiles found yet."
      );
    } catch (err) {
      setPros([]);
      setError(err instanceof Error ? err.message : "Search failed");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <PageShell className="max-w-4xl">
      <PageHeader
        title="Find a professional"
        description="Directory matches by specialty and location — informational only, not an endorsement or attorney referral network."
      />

      <SurfaceCard className="hover:shadow-sm">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            void load();
          }}
        >
          <div className="min-w-0 flex-1 space-y-1.5 sm:min-w-[200px]">
            <label htmlFor="pro-spec" className="text-xs font-medium text-muted-foreground">
              Specialization
            </label>
            <Input
              id="pro-spec"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Property Lawyer"
            />
          </div>
          <div className="min-w-0 flex-1 space-y-1.5 sm:min-w-[140px]">
            <label htmlFor="pro-city" className="text-xs font-medium text-muted-foreground">
              City
            </label>
            <Input
              id="pro-city"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="City"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Search className="size-4" />
              )}
              Search
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={loading}
              onClick={() => {
                if (!navigator.geolocation) {
                  setError("Geolocation is not available in this browser.");
                  return;
                }
                setLoading(true);
                setStatus("Waiting for location permission…");
                navigator.geolocation.getCurrentPosition(
                  (pos) => {
                    const next = {
                      latitude: pos.coords.latitude,
                      longitude: pos.coords.longitude,
                    };
                    setLoc(next);
                    void load(next);
                  },
                  () => {
                    setLoading(false);
                    setError("Location permission denied. Try a city search.");
                  }
                );
              }}
            >
              <MapPin className="size-4" />
              Use my location
            </Button>
          </div>
        </form>
      </SurfaceCard>

      <div className="mt-4 space-y-3">
        {error ? <StatusBanner tone="error">{error}</StatusBanner> : null}
        {!error && status && !loading ? (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {status}
          </p>
        ) : null}
        {loading ? <LoadingBlock label="Searching professionals…" /> : null}

        {!loading && !pros.length ? (
          <EmptyState
            title="No profiles yet"
            description="Try another city or specialty, or check back after the directory is updated."
          />
        ) : null}

        {!loading && pros.length ? (
          <ul className="space-y-3">
            {pros.map((p) => (
              <li key={p.id}>
                <SurfaceCard className="transition-transform duration-150 hover:-translate-y-0.5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h2 className="text-base font-semibold text-foreground">{p.name}</h2>
                      <p className="mt-0.5 text-sm text-muted-foreground">
                        {p.specialization}
                        {p.city ? ` · ${p.city}` : ""}
                      </p>
                    </div>
                    {p.verified ? (
                      <span className="rounded-md border border-success/30 bg-success/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-foreground">
                        Verified
                      </span>
                    ) : null}
                  </div>
                  {p.distance_km != null ? (
                    <p className="mt-2 text-sm font-medium text-primary">
                      {p.distance_km.toFixed(1)} km away
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {p.phone ? (
                      <ContactChip href={`tel:${p.phone}`}>Call</ContactChip>
                    ) : null}
                    {p.email ? (
                      <ContactChip href={`mailto:${p.email}`}>Email</ContactChip>
                    ) : null}
                    {p.website ? (
                      <ContactChip href={p.website}>Website</ContactChip>
                    ) : null}
                  </div>
                </SurfaceCard>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <p
        className={cn(
          "mt-8 text-center text-xs leading-relaxed text-muted-foreground"
        )}
      >
        Always verify credentials independently before engaging a professional.
      </p>
    </PageShell>
  );
}
