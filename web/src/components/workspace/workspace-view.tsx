"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, MoreHorizontal } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  ContactChip,
  LoadingBlock,
  PageShell,
  PanelHeader,
  SegmentedTabs,
  StatusBanner,
  SurfaceCard,
  SurfaceInset,
} from "@/components/ui/page-shell";
import { CitationList } from "@/components/patterns/citation-list";
import { DisclaimerCallout } from "@/components/patterns/disclaimer-callout";
import { ConfirmDialog, EmptyState, Input, StatusBadge } from "@/design-system";
import { AskChat } from "@/components/chat/ask-chat";
import { api, apiUrl, errorMessage } from "@/lib/api";

// react-pdf / pdf.js touch DOMMatrix at import time — keep off the SSR/prerender path.
const PdfReader = dynamic(
  () =>
    import("@/components/reader/pdf-reader").then((m) => m.PdfReader),
  {
    ssr: false,
    loading: () => <LoadingBlock label="Loading reader…" />,
  }
);
import {
  WORKSPACE_MODES,
  parseWorkspaceMode,
  routes,
  type WorkspaceMode,
} from "@/lib/routes";
import type {
  Confidence,
  ConsultSection,
  ExplainSection,
  Professional,
  RiskItem,
} from "@/lib/types";
import { writeLastWorkspace } from "@/lib/workspace-activity";
import { cn } from "@/lib/utils";

const PRIMARY_MODES: WorkspaceMode[] = ["ask", "read"];
const TOOL_MODES: WorkspaceMode[] = [
  "explain",
  "risks",
  "consult",
  "compare",
  "connect",
];

function isLoadingStatus(status: string): boolean {
  return (
    status.includes("…") ||
    /Retrieving|Scanning|Building/i.test(status)
  );
}

function isErrorStatus(status: string): boolean {
  return /failed|Error|Could not/i.test(status);
}

export function WorkspaceView() {
  const search = useSearchParams();
  const router = useRouter();
  const { token, docs, readyDocs, refreshDocs, refreshUsage } = useAuth();

  const docId = search.get("id");
  const mode = parseWorkspaceMode(search.get("mode"));
  const activeDoc = docs.find((d) => d.id === docId) || null;
  const isReady = (activeDoc?.status || "").toUpperCase() === "READY";

  const [explain, setExplain] = useState<{
    status: string;
    sections: ExplainSection[];
    disclaimer: string;
    confidence?: Confidence | null;
  }>({ status: "", sections: [], disclaimer: "" });
  const [risks, setRisks] = useState<{
    status: string;
    items: RiskItem[];
    disclaimer: string;
  }>({ status: "", items: [], disclaimer: "" });
  const [consult, setConsult] = useState<{
    status: string;
    sections: ConsultSection[];
    disclaimer: string;
    canPdf: boolean;
  }>({ status: "", sections: [], disclaimer: "", canPdf: false });
  const [expert, setExpert] = useState<{
    status: string;
    category: string;
    reason: string;
    disclaimer: string;
    pros: Professional[];
    dirStatus: string;
  }>({
    status: "",
    category: "",
    reason: "",
    disclaimer: "",
    pros: [],
    dirStatus: "",
  });
  const [cmpB, setCmpB] = useState("");
  const [cmpQ, setCmpQ] = useState("Compare payment, termination, and liability terms.");
  const [cmpOut, setCmpOut] = useState("");
  const [cmpConf, setCmpConf] = useState<Confidence | null>(null);
  const [city, setCity] = useState("");
  const locationRef = useRef<{ latitude: number; longitude: number } | null>(null);
  const ranMode = useRef<string>("");

  const setMode = useCallback(
    (m: WorkspaceMode) => {
      if (!docId) return;
      router.replace(routes.workspace(docId, m));
    },
    [docId, router]
  );

  useEffect(() => {
    if (!docId || !activeDoc) return;
    writeLastWorkspace({
      documentId: docId,
      filename: activeDoc.original_filename,
      mode,
      at: new Date().toISOString(),
    });
  }, [docId, mode, activeDoc]);

  const runExplain = useCallback(async () => {
    if (!token || !docId || !isReady) return;
    setExplain({
      status: "Retrieving excerpts and generating explanation…",
      sections: [],
      disclaimer: "",
    });
    try {
      const data = await api<{
        filename: string;
        processing_time: number;
        sections: ExplainSection[];
        disclaimer?: string;
      } & Confidence>("/explain", {
        method: "POST",
        token,
        json: { document_id: docId },
      });
      setExplain({
        status: `Explanation for ${data.filename} · ${data.processing_time}s`,
        sections: data.sections || [],
        disclaimer: data.disclaimer || "",
        confidence: data,
      });
    } catch (err) {
      setExplain((s) => ({
        ...s,
        status: err instanceof Error ? err.message : "Explain failed",
      }));
    }
  }, [token, docId, isReady]);

  const runRisks = useCallback(async () => {
    if (!token || !docId || !isReady) return;
    setRisks({ status: "Scanning for common legal risks…", items: [], disclaimer: "" });
    try {
      const data = await api<{
        filename: string;
        processing_time: number;
        risks: RiskItem[];
        disclaimer?: string;
      }>("/risks", {
        method: "POST",
        token,
        json: { document_id: docId },
      });
      const flagged = (data.risks || []).filter((r) => r.evidence_found).length;
      setRisks({
        status: `Risk scan for ${data.filename} · ${flagged} flagged · ${data.processing_time}s`,
        items: data.risks || [],
        disclaimer: data.disclaimer || "",
      });
    } catch (err) {
      setRisks((s) => ({
        ...s,
        status: err instanceof Error ? err.message : "Risk scan failed",
      }));
    }
  }, [token, docId, isReady]);

  const runConsult = useCallback(async () => {
    if (!token || !docId || !isReady) return;
    setConsult({
      status: "Building your briefing…",
      sections: [],
      disclaimer: "",
      canPdf: false,
    });
    try {
      const data = await api<{
        filename: string;
        processing_time: number;
        sections: ConsultSection[];
        disclaimer?: string;
      }>("/prepare-consultation", {
        method: "POST",
        token,
        json: { document_id: docId },
      });
      setConsult({
        status: `Consultation prep for ${data.filename} · ${data.processing_time}s`,
        sections: data.sections || [],
        disclaimer: data.disclaimer || "",
        canPdf: true,
      });
    } catch (err) {
      setConsult((s) => ({
        ...s,
        status: err instanceof Error ? err.message : "Consultation prep failed",
        canPdf: false,
      }));
    }
  }, [token, docId, isReady]);

  const fetchPros = useCallback(
    async (category?: string) => {
      if (!token) return;
      const params = new URLSearchParams();
      if (category) params.set("specialization", category);
      if (city.trim()) params.set("city", city.trim());
      if (locationRef.current) {
        params.set("latitude", String(locationRef.current.latitude));
        params.set("longitude", String(locationRef.current.longitude));
      }
      setExpert((e) => ({ ...e, dirStatus: "Finding professionals…" }));
      try {
        const pros = await api<Professional[]>(
          `/professionals/recommend?${params.toString()}`,
          { token }
        );
        setExpert((e) => ({
          ...e,
          pros: pros || [],
          dirStatus: pros?.length
            ? `${pros.length} match${pros.length === 1 ? "" : "es"}`
            : "No directory profiles found yet.",
        }));
      } catch (err) {
        setExpert((e) => ({
          ...e,
          dirStatus: err instanceof Error ? err.message : "Directory lookup failed",
        }));
      }
    },
    [token, city]
  );

  const runExpert = useCallback(async () => {
    if (!token || !docId || !isReady) return;
    setExpert((e) => ({
      ...e,
      status: "Analyzing document…",
      category: "",
      reason: "",
    }));
    try {
      const data = await api<{
        filename: string;
        processing_time: number;
        category: string;
        reason: string;
        disclaimer?: string;
      }>("/recommend-expert", {
        method: "POST",
        token,
        json: { document_id: docId },
      });
      setExpert((e) => ({
        ...e,
        status: `Recommendation for ${data.filename} · ${data.processing_time}s`,
        category: data.category || "",
        reason: data.reason || "",
        disclaimer: data.disclaimer || "",
      }));
      await fetchPros(data.category);
    } catch (err) {
      setExpert((e) => ({
        ...e,
        status: err instanceof Error ? err.message : "Recommendation failed",
      }));
    }
  }, [token, docId, isReady, fetchPros]);

  useEffect(() => {
    if (!docId || !isReady) return;
    const key = `${docId}:${mode}`;
    if (ranMode.current === key) return;
    ranMode.current = key;
    if (mode === "explain") void runExplain();
    if (mode === "risks") void runRisks();
    if (mode === "consult") void runConsult();
    if (mode === "connect") void runExpert();
  }, [docId, isReady, mode, runExplain, runRisks, runConsult, runExpert]);

  async function exportConsultPdf() {
    if (!token || !docId) return;
    setConsult((s) => ({ ...s, status: "Generating PDF…" }));
    try {
      const res = await fetch(apiUrl("/prepare-consultation/pdf"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ document_id: docId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, "PDF export failed"));
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "consultation-briefing.pdf";
      a.click();
      setConsult((s) => ({ ...s, status: "PDF downloaded." }));
    } catch (err) {
      setConsult((s) => ({
        ...s,
        status: err instanceof Error ? err.message : "PDF export failed",
      }));
    }
  }

  if (!docId) {
    return (
      <PageShell className="max-w-xl">
        <EmptyState
          title="Choose a document"
          description="Open a file from your library to ask questions or run analysis."
          action={
            <Button variant="primary" onClick={() => router.push(routes.documents)}>
              Go to documents
            </Button>
          }
        />
      </PageShell>
    );
  }

  const explainLoading = isLoadingStatus(explain.status);
  const risksLoading = isLoadingStatus(risks.status);
  const consultLoading = isLoadingStatus(consult.status);
  const expertLoading = isLoadingStatus(expert.status);
  const dirLoading = isLoadingStatus(expert.dirStatus);
  const cmpLoading = isLoadingStatus(cmpOut);

  return (
    <PageShell
      wide={mode === "read"}
      className="flex min-h-[calc(100vh-3.5rem)] flex-col py-4 sm:py-5"
    >
      <div className="flex flex-col gap-4 border-b border-border pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href={routes.documents}
                className="text-[13px] text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Documents
              </Link>
              <span className="text-border" aria-hidden>
                /
              </span>
              <StatusBadge status={activeDoc?.status} />
            </div>
            <h1 className="mt-1.5 truncate font-display text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              {activeDoc?.original_filename || "Document"}
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <SegmentedTabs
              ariaLabel="Primary workspace mode"
              value={PRIMARY_MODES.includes(mode) ? mode : ""}
              onChange={(id) => setMode(parseWorkspaceMode(id))}
              items={PRIMARY_MODES.map((id) => ({
                id,
                label: WORKSPACE_MODES.find((m) => m.id === id)?.label || id,
                disabled: !isReady && id !== "ask" && id !== "read",
              }))}
              className="w-auto"
            />

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  size="sm"
                  variant={TOOL_MODES.includes(mode) ? "secondary" : "outline"}
                  className="gap-1.5"
                  disabled={!isReady}
                >
                  {TOOL_MODES.includes(mode)
                    ? WORKSPACE_MODES.find((m) => m.id === mode)?.label
                    : "Analyze"}
                  <ChevronDown className="size-3.5 opacity-70" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                {TOOL_MODES.map((id) => (
                  <DropdownMenuItem
                    key={id}
                    disabled={!isReady}
                    onSelect={() => setMode(id)}
                    className={cn(mode === id && "bg-muted")}
                  >
                    {WORKSPACE_MODES.find((m) => m.id === id)?.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon-sm" variant="ghost" aria-label="More actions">
                  <MoreHorizontal className="size-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuItem
                  disabled={!docId}
                  onSelect={() => {
                    void (async () => {
                      if (!token || !docId) return;
                      const data = await api<{ content: string; filename?: string }>(
                        `/documents/${docId}/export`,
                        { token }
                      );
                      const a = document.createElement("a");
                      a.href = URL.createObjectURL(
                        new Blob([data.content], { type: "text/plain" })
                      );
                      a.download = data.filename || "export.txt";
                      a.click();
                    })();
                  }}
                >
                  Export notes
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <ConfirmDialog
              title="Remove this document?"
              description="This permanently deletes the document and its analysis data from your library."
              confirmLabel="Delete"
              cancelLabel="Cancel"
              tone="danger"
              trigger={
                <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive">
                  Delete
                </Button>
              }
              onConfirm={async () => {
                if (!token || !docId) return;
                await api(`/documents/${docId}`, { method: "DELETE", token });
                await refreshDocs();
                router.push(routes.documents);
              }}
            />
          </div>
        </div>

        {!isReady ? (
          <StatusBanner tone="warning">
            This document isn’t ready yet. Wait for processing to finish, or return to the library
            if it failed.
          </StatusBanner>
        ) : null}

        {TOOL_MODES.includes(mode) ? (
          <p className="text-[13px] text-muted-foreground">
            Analyzing with{" "}
            <span className="font-medium text-foreground">
              {WORKSPACE_MODES.find((m) => m.id === mode)?.label}
            </span>
            . Switch back to Ask or Read anytime.
          </p>
        ) : null}
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        {mode === "ask" && docId ? (
          <AskChat
            key={docId}
            token={token}
            documentId={docId}
            isReady={isReady}
            onUsageRefresh={refreshUsage}
          />
        ) : null}

        {mode === "read" && docId ? (
          <PdfReader
            key={docId}
            token={token}
            documentId={docId}
            filename={activeDoc?.original_filename}
          />
        ) : null}

        {mode === "explain" && (
          <SurfaceCard>
            <PanelHeader
              title="Document explanation"
              action={
                <Button size="sm" variant="ghost" onClick={runExplain}>
                  Re-run
                </Button>
              }
            />
            {isErrorStatus(explain.status) ? (
              <StatusBanner tone="error">{explain.status}</StatusBanner>
            ) : null}
            {explainLoading && explain.sections.length === 0 ? (
              <LoadingBlock label={explain.status} />
            ) : (
              <>
                {explainLoading ? (
                  <LoadingBlock className="mb-3 py-6" label={explain.status} />
                ) : explain.status && !isErrorStatus(explain.status) ? (
                  <p className="mb-2 text-sm text-muted-foreground">{explain.status}</p>
                ) : null}
                {!isErrorStatus(explain.status) ? (
                  <ConfidenceBadge data={explain.confidence} />
                ) : null}
                {!isErrorStatus(explain.status) && explain.sections.length === 0 && !explainLoading ? (
                  <EmptyState
                    className="mt-3"
                    title="No explanation yet"
                    description="Run explanation to break this document into plain-language sections."
                  />
                ) : null}
                {explain.sections.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {explain.sections.map((s, i) => (
                      <SurfaceInset key={i}>
                        <h3 className="font-medium text-foreground">{s.title}</h3>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                          {s.content}
                        </p>
                        <CitationList citations={s.citations} documentId={docId} />
                      </SurfaceInset>
                    ))}
                  </div>
                ) : null}
                {explain.disclaimer ? (
                  <p className="mt-3 text-xs text-muted-foreground">{explain.disclaimer}</p>
                ) : null}
              </>
            )}
          </SurfaceCard>
        )}

        {mode === "risks" && (
          <SurfaceCard>
            <PanelHeader
              title="Risk highlights"
              action={
                <Button size="sm" variant="ghost" onClick={runRisks}>
                  Re-run
                </Button>
              }
            />
            {isErrorStatus(risks.status) ? (
              <StatusBanner tone="error">{risks.status}</StatusBanner>
            ) : null}
            {risksLoading && risks.items.length === 0 ? (
              <LoadingBlock label={risks.status} />
            ) : (
              <>
                {risksLoading ? (
                  <LoadingBlock className="mb-3 py-6" label={risks.status} />
                ) : risks.status && !isErrorStatus(risks.status) ? (
                  <p className="mb-2 text-sm text-muted-foreground">{risks.status}</p>
                ) : null}
                {!isErrorStatus(risks.status) && risks.items.length === 0 && !risksLoading ? (
                  <EmptyState
                    className="mt-3"
                    title="No risks listed"
                    description="Run a risk scan to surface common clauses that may need attention."
                  />
                ) : null}
                {risks.items.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {risks.items.map((r, i) => (
                      <SurfaceInset key={i}>
                        <div className="flex justify-between gap-2">
                          <h3 className="font-medium text-foreground">{r.title}</h3>
                          <span className="text-xs uppercase text-muted-foreground">
                            {r.evidence_found && r.severity ? r.severity : "No evidence"}
                          </span>
                        </div>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                          {r.explanation}
                        </p>
                        <CitationList citations={r.citations} documentId={docId} />
                        {r.evidence_found ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            className="mt-2"
                            onClick={() => {
                              sessionStorage.setItem(
                                "copilot_ask_draft",
                                `Tell me more about: ${r.title}`
                              );
                              setMode("ask");
                            }}
                          >
                            Ask about this
                          </Button>
                        ) : null}
                      </SurfaceInset>
                    ))}
                  </div>
                ) : null}
                {risks.disclaimer ? (
                  <p className="mt-3 text-xs text-muted-foreground">{risks.disclaimer}</p>
                ) : null}
              </>
            )}
          </SurfaceCard>
        )}

        {mode === "consult" && (
          <SurfaceCard>
            <PanelHeader
              title="Consultation briefing"
              action={
                <Button size="sm" variant="ghost" onClick={runConsult}>
                  Re-run
                </Button>
              }
            />
            {isErrorStatus(consult.status) ? (
              <StatusBanner tone="error">{consult.status}</StatusBanner>
            ) : null}
            {consultLoading && consult.sections.length === 0 ? (
              <LoadingBlock label={consult.status} />
            ) : (
              <>
                {consultLoading ? (
                  <LoadingBlock className="mb-3 py-6" label={consult.status} />
                ) : consult.status && !isErrorStatus(consult.status) ? (
                  <p className="mb-2 text-sm text-muted-foreground">{consult.status}</p>
                ) : null}
                {!isErrorStatus(consult.status) &&
                consult.sections.length === 0 &&
                !consultLoading ? (
                  <EmptyState
                    className="mt-3"
                    title="No briefing yet"
                    description="Build a consultation prep briefing from this document."
                  />
                ) : null}
                {consult.sections.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {consult.sections.map((s, i) => (
                      <SurfaceInset key={i}>
                        <h3 className="font-medium text-foreground">{s.title}</h3>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-muted-foreground">
                          {s.content}
                        </p>
                        <CitationList citations={s.citations} documentId={docId} />
                      </SurfaceInset>
                    ))}
                  </div>
                ) : null}
              </>
            )}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" disabled={!consult.canPdf} onClick={exportConsultPdf}>
                Download PDF briefing
              </Button>
              <Button onClick={() => setMode("connect")}>Find a professional</Button>
            </div>
            {consult.disclaimer ? (
              <p className="mt-3 text-xs text-muted-foreground">{consult.disclaimer}</p>
            ) : null}
          </SurfaceCard>
        )}

        {mode === "compare" && (
          <SurfaceCard>
            <PanelHeader
              title="Compare contracts"
              description="Compare this document with another ready agreement."
            />
            <div className="grid gap-2 sm:grid-cols-2">
              <SurfaceInset className="text-sm text-muted-foreground">
                A: {activeDoc?.original_filename}
              </SurfaceInset>
              <select
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={cmpB}
                onChange={(e) => setCmpB(e.target.value)}
              >
                <option value="">Second document</option>
                {readyDocs
                  .filter((d) => d.id !== docId)
                  .map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.original_filename}
                    </option>
                  ))}
              </select>
            </div>
            <Input className="mt-3" value={cmpQ} onChange={(e) => setCmpQ(e.target.value)} />
            <Button
              className="mt-3"
              onClick={async () => {
                if (!token || !docId || !cmpB || cmpB === docId) {
                  setCmpOut("Pick a different second document.");
                  return;
                }
                setCmpOut("Comparing…");
                try {
                  const data = await api<{ answer: string } & Confidence>("/compare", {
                    method: "POST",
                    token,
                    json: {
                      document_id_a: docId,
                      document_id_b: cmpB,
                      question: cmpQ,
                    },
                  });
                  setCmpOut(data.answer);
                  setCmpConf(data);
                } catch (err) {
                  setCmpOut(err instanceof Error ? err.message : "Compare failed");
                  setCmpConf(null);
                }
              }}
            >
              Run comparison
            </Button>
            {cmpLoading ? (
              <LoadingBlock className="mt-3" label={cmpOut} />
            ) : isErrorStatus(cmpOut) ? (
              <StatusBanner tone="error" className="mt-3">
                {cmpOut}
              </StatusBanner>
            ) : cmpOut ? (
              <SurfaceInset className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
                {cmpOut}
                <ConfidenceBadge data={cmpConf} />
                <DisclaimerCallout className="mt-2" />
              </SurfaceInset>
            ) : (
              <EmptyState
                className="mt-3"
                title="No comparison yet"
                description="Choose a second document and run a comparison to see side-by-side insights."
              />
            )}
          </SurfaceCard>
        )}

        {mode === "connect" && (
          <SurfaceCard>
            <PanelHeader
              title="Find the right professional"
              action={
                <Link
                  href={routes.professionals()}
                  className="text-sm text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Open directory →
                </Link>
              }
            />
            {isErrorStatus(expert.status) ? (
              <StatusBanner tone="error">{expert.status}</StatusBanner>
            ) : expertLoading && !expert.category ? (
              <LoadingBlock label={expert.status} />
            ) : expertLoading ? (
              <LoadingBlock className="mb-3 py-6" label={expert.status} />
            ) : expert.status && !isErrorStatus(expert.status) ? (
              <p className="mb-2 text-sm text-muted-foreground">{expert.status}</p>
            ) : null}
            {expert.category ? (
              <SurfaceInset className="mt-1">
                <p className="text-xs uppercase text-muted-foreground">Recommended category</p>
                <p className="text-xl font-semibold text-primary">{expert.category}</p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
                  {expert.reason}
                </p>
              </SurfaceInset>
            ) : !expertLoading && !isErrorStatus(expert.status) && !expert.status ? (
              <EmptyState
                className="mt-1"
                title="No recommendation yet"
                description="Analyze this document to suggest a professional category."
              />
            ) : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="primary" onClick={runExpert}>
                Recommend category
              </Button>
              <Button
                onClick={() => {
                  if (!navigator.geolocation) {
                    setExpert((e) => ({
                      ...e,
                      dirStatus: "Geolocation is not available in this browser.",
                    }));
                    return;
                  }
                  setExpert((e) => ({
                    ...e,
                    dirStatus: "Waiting for location permission…",
                  }));
                  navigator.geolocation.getCurrentPosition(
                    (pos) => {
                      locationRef.current = {
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                      };
                      fetchPros(expert.category);
                    },
                    () =>
                      setExpert((e) => ({
                        ...e,
                        dirStatus: "Location permission denied. Try a city search.",
                      }))
                  );
                }}
              >
                Use my location
              </Button>
            </div>
            <form
              className="mt-3 flex flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                fetchPros(expert.category);
              }}
            >
              <Input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="Or search by city…"
                className="max-w-xs"
              />
              <Button type="submit">Search city</Button>
            </form>
            {isErrorStatus(expert.dirStatus) ? (
              <StatusBanner tone="error" className="mt-3">
                {expert.dirStatus}
              </StatusBanner>
            ) : null}
            {dirLoading && expert.pros.length === 0 ? (
              <LoadingBlock className="mt-3" label={expert.dirStatus} />
            ) : (
              <>
                {dirLoading ? (
                  <LoadingBlock className="mt-3 py-6" label={expert.dirStatus} />
                ) : expert.dirStatus && !isErrorStatus(expert.dirStatus) ? (
                  <p className="mt-3 text-sm text-muted-foreground">{expert.dirStatus}</p>
                ) : null}
                {!dirLoading &&
                !isErrorStatus(expert.dirStatus) &&
                expert.pros.length === 0 ? (
                  <EmptyState
                    className="mt-3"
                    title="No professionals listed"
                    description="Search by city or allow location to find directory matches."
                  />
                ) : null}
                {expert.pros.length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {expert.pros.map((p) => (
                      <SurfaceInset key={p.id}>
                        <div className="flex justify-between gap-2">
                          <h3 className="font-medium text-foreground">{p.name}</h3>
                          {p.verified ? (
                            <span className="text-xs text-success">Verified</span>
                          ) : null}
                        </div>
                        <p className="text-sm text-muted-foreground">{p.specialization}</p>
                        {p.distance_km != null ? (
                          <p className="text-sm text-primary">{p.distance_km.toFixed(1)} km</p>
                        ) : null}
                        <div className="mt-2 flex flex-wrap gap-2">
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
                      </SurfaceInset>
                    ))}
                  </div>
                ) : null}
              </>
            )}
            {expert.disclaimer ? (
              <p className="mt-3 text-xs text-muted-foreground">{expert.disclaimer}</p>
            ) : null}
          </SurfaceCard>
        )}
      </div>
    </PageShell>
  );
}
