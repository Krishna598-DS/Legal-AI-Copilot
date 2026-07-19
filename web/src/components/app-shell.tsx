"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, apiUrl, errorMessage, getToken, setToken } from "@/lib/api";
import { personaActions } from "@/lib/dashboard-actions";
import type {
  ChatMessage,
  Citation,
  Confidence,
  ConsultSection,
  DashboardAction,
  DocumentRow,
  ExplainSection,
  Professional,
  RiskItem,
  User,
} from "@/lib/types";
import { AuthPanel } from "./auth-panel";
import { ConfidenceBadge } from "./confidence-badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

type View = "dashboard" | "workspace";
type Bubble = {
  id: string;
  role: string;
  content: string;
  sources?: Citation[];
  confidence?: Confidence | null;
};

function docLabel(d: DocumentRow) {
  const status = (d.status || "").toUpperCase();
  if (status === "READY") return `${d.original_filename} · Ready`;
  if (status === "FAILED") return `${d.original_filename} · Failed`;
  return `${d.original_filename} · Processing…`;
}

function CiteChips({ citations }: { citations?: Citation[] }) {
  if (!citations?.length) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      {citations.map((c, i) => (
        <span
          key={i}
          className="rounded-full border border-slate-600 bg-teal-950/50 px-2 py-0.5 text-xs text-teal-300"
        >
          {c.filename || "doc"}
          {c.page != null ? ` p.${c.page}` : ""}
        </span>
      ))}
    </div>
  );
}

export function AppShell() {
  const [booting, setBooting] = useState(true);
  const [token, setTok] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [docs, setDocs] = useState<DocumentRow[]>([]);
  const [view, setView] = useState<View>("dashboard");
  const [activeDocId, setActiveDocId] = useState<string | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [usage, setUsage] = useState("");
  const [hint, setHint] = useState("");
  const [status, setStatus] = useState("Ready");
  const [uploadMsg, setUploadMsg] = useState("");
  const [askDraft, setAskDraft] = useState("");
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [file, setFile] = useState<File | null>(null);

  const [explain, setExplain] = useState<{
    open: boolean;
    status: string;
    sections: ExplainSection[];
    disclaimer: string;
    confidence?: Confidence | null;
  }>({ open: false, status: "", sections: [], disclaimer: "" });
  const [risks, setRisks] = useState<{
    open: boolean;
    status: string;
    items: RiskItem[];
    disclaimer: string;
  }>({ open: false, status: "", items: [], disclaimer: "" });
  const [consult, setConsult] = useState<{
    open: boolean;
    status: string;
    sections: ConsultSection[];
    disclaimer: string;
    canPdf: boolean;
  }>({ open: false, status: "", sections: [], disclaimer: "", canPdf: false });
  const [expert, setExpert] = useState<{
    open: boolean;
    status: string;
    category: string;
    reason: string;
    disclaimer: string;
    pros: Professional[];
    dirStatus: string;
  }>({
    open: false,
    status: "",
    category: "",
    reason: "",
    disclaimer: "",
    pros: [],
    dirStatus: "",
  });
  const [adminOpen, setAdminOpen] = useState(false);
  const [adminStats, setAdminStats] = useState("");
  const [cmpA, setCmpA] = useState("");
  const [cmpB, setCmpB] = useState("");
  const [cmpQ, setCmpQ] = useState("Compare payment, termination, and liability terms.");
  const [cmpOut, setCmpOut] = useState("");
  const [cmpConf, setCmpConf] = useState<Confidence | null>(null);
  const [city, setCity] = useState("");
  const locationRef = useRef<{ latitude: number; longitude: number } | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  const readyDocs = useMemo(
    () => docs.filter((d) => (d.status || "").toUpperCase() === "READY"),
    [docs]
  );
  const activeDoc = docs.find((d) => d.id === activeDocId) || null;

  const refreshDocs = useCallback(async (t: string) => {
    const list = await api<DocumentRow[]>("/documents", { token: t });
    setDocs(list);
    return list;
  }, []);

  const refreshUsage = useCallback(async (t: string) => {
    try {
      const u = await api<{
        questions_last_hour: number;
        questions_limit: number;
        uploads_last_hour: number;
        uploads_limit: number;
        documents_owned: number;
        documents_limit: number;
      }>("/account/usage", { token: t });
      setUsage(
        `Questions ${u.questions_last_hour}/${u.questions_limit} · Uploads ${u.uploads_last_hour}/${u.uploads_limit} · Documents ${u.documents_owned}/${u.documents_limit}`
      );
    } catch {
      setUsage("");
    }
  }, []);

  const afterAuth = useCallback(
    async (access: string) => {
      setToken(access);
      setTok(access);
      const me = await api<User>("/auth/me", { token: access });
      setUser(me);
      await refreshDocs(access);
      await refreshUsage(access);
      try {
        await api("/admin/stats", { token: access });
        setIsAdmin(true);
      } catch {
        setIsAdmin(false);
      }
      setView("dashboard");
      setBooting(false);
    },
    [refreshDocs, refreshUsage]
  );

  useEffect(() => {
    const existing = getToken();
    if (!existing) {
      setBooting(false);
      return;
    }
    afterAuth(existing).catch(() => {
      setToken(null);
      setTok(null);
      setBooting(false);
    });
  }, [afterAuth]);

  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight });
  }, [bubbles]);

  async function selectDoc(id: string, t = token) {
    if (!t) return;
    setActiveDocId(id);
    const messages = await api<ChatMessage[]>(`/documents/${id}/messages`, { token: t });
    setBubbles(
      messages.map((m, i) => ({
        id: `${id}-${i}`,
        role: m.role,
        content: m.content,
      }))
    );
  }

  async function waitReady(documentId: string, t: string) {
    const started = Date.now();
    while (Date.now() - started < 120000) {
      const doc = await api<DocumentRow>(`/documents/${documentId}`, { token: t });
      const st = (doc.status || "").toUpperCase();
      if (st === "READY") return doc;
      if (st === "FAILED") throw new Error(doc.processing_error || "Processing failed");
      setUploadMsg(`Processing… (${st})`);
      await new Promise((r) => setTimeout(r, 1000));
    }
    throw new Error("Timed out waiting for document processing");
  }

  function goWorkspace(opts: { hint?: string; prompt?: string; showExpert?: boolean } = {}) {
    setView("workspace");
    setHint(opts.hint || "");
    if (opts.prompt) setAskDraft(opts.prompt);
    if (opts.showExpert) setExpert((e) => ({ ...e, open: true }));
  }

  async function ensureReadyDoc() {
    if (!token) return null;
    const list = await refreshDocs(token);
    const ready = list.filter((d) => (d.status || "").toUpperCase() === "READY");
    if (!ready.length) return null;
    const active = list.find((d) => d.id === activeDocId);
    if (!active || (active.status || "").toUpperCase() !== "READY") {
      await selectDoc(ready[0].id, token);
      return ready[0];
    }
    return active;
  }

  async function handleAction(action: DashboardAction) {
    const needsDoc = !["upload", "search"].includes(action.id);
    if (action.id === "upload") {
      goWorkspace({
        hint: "Choose a PDF or TXT to upload. Analysis runs in the background.",
      });
      return;
    }
    if (action.id === "search" || action.id === "compare") {
      goWorkspace({
        hint:
          action.id === "compare"
            ? "Pick two documents below to compare."
            : "Select a document, then ask questions.",
      });
      return;
    }
    const doc = await ensureReadyDoc();
    if (needsDoc && !doc) {
      goWorkspace({
        hint: "Upload a document first — then this action can use it.",
      });
      return;
    }
    goWorkspace({ hint: action.title, prompt: action.prompt || "" });
    if (action.id === "explain") await runExplain();
    if (action.id === "risks") await runRisks();
    if (action.id === "consult") await runConsult();
    if (action.id === "expert") {
      setExpert((e) => ({ ...e, open: true }));
      await runExpert();
    }
  }

  async function runExplain() {
    if (!token) return;
    const doc = await ensureReadyDoc();
    if (!doc) {
      goWorkspace({ hint: "Upload a document first — then Explain can run." });
      return;
    }
    setExplain({
      open: true,
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
        confidence_level?: string;
        confidence_score?: number;
        recommendation?: string;
      }>("/explain", {
        method: "POST",
        token,
        json: { document_id: doc.id },
      });
      setExplain({
        open: true,
        status: `Explanation for ${data.filename} · ${data.processing_time}s`,
        sections: data.sections || [],
        disclaimer: data.disclaimer || "",
        confidence: data,
      });
    } catch (err) {
      setExplain((s) => ({
        ...s,
        open: true,
        status: err instanceof Error ? err.message : "Explain failed",
      }));
    }
  }

  async function runRisks() {
    if (!token) return;
    const doc = await ensureReadyDoc();
    if (!doc) {
      goWorkspace({ hint: "Upload a document first — then Detect risks can run." });
      return;
    }
    setRisks({
      open: true,
      status: "Scanning for common legal risks…",
      items: [],
      disclaimer: "",
    });
    try {
      const data = await api<{
        filename: string;
        processing_time: number;
        risks: RiskItem[];
        disclaimer?: string;
      }>("/risks", {
        method: "POST",
        token,
        json: { document_id: doc.id },
      });
      const flagged = (data.risks || []).filter((r) => r.evidence_found).length;
      setRisks({
        open: true,
        status: `Risk scan for ${data.filename} · ${flagged} flagged · ${data.processing_time}s`,
        items: data.risks || [],
        disclaimer: data.disclaimer || "",
      });
    } catch (err) {
      setRisks((s) => ({
        ...s,
        open: true,
        status: err instanceof Error ? err.message : "Risk scan failed",
      }));
    }
  }

  async function runConsult() {
    if (!token) return;
    const doc = await ensureReadyDoc();
    if (!doc) {
      goWorkspace({ hint: "Upload a document first — then Prepare for consultation can run." });
      return;
    }
    setConsult({
      open: true,
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
        json: { document_id: doc.id },
      });
      setConsult({
        open: true,
        status: `Consultation prep for ${data.filename} · ${data.processing_time}s`,
        sections: data.sections || [],
        disclaimer: data.disclaimer || "",
        canPdf: true,
      });
    } catch (err) {
      setConsult((s) => ({
        ...s,
        open: true,
        status: err instanceof Error ? err.message : "Consultation prep failed",
        canPdf: false,
      }));
    }
  }

  async function exportConsultPdf() {
    if (!token || !activeDocId) return;
    setConsult((s) => ({ ...s, status: "Generating PDF…" }));
    try {
      const res = await fetch(apiUrl("/prepare-consultation/pdf"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ document_id: activeDocId }),
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

  async function runExpert() {
    if (!token) return;
    const doc = await ensureReadyDoc();
    if (!doc) {
      goWorkspace({
        hint: "Upload a document first — then we can recommend a professional category.",
      });
      return;
    }
    setExpert((e) => ({
      ...e,
      open: true,
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
        json: { document_id: doc.id },
      });
      setExpert((e) => ({
        ...e,
        open: true,
        status: `Recommendation for ${data.filename} · ${data.processing_time}s`,
        category: data.category || "",
        reason: data.reason || "",
        disclaimer: data.disclaimer || "",
      }));
      await fetchPros(data.category);
    } catch (err) {
      setExpert((e) => ({
        ...e,
        open: true,
        status: err instanceof Error ? err.message : "Recommendation failed",
      }));
    }
  }

  async function fetchPros(category?: string) {
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
  }

  async function onUpload() {
    if (!token || !file) {
      setUploadMsg("Choose a PDF or TXT first.");
      return;
    }
    setUploadMsg("Processing…");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(apiUrl("/documents/upload"), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      if (!res.ok) throw new Error(errorMessage(data, "Upload failed"));
      const id = data.document?.id || data.id;
      const ready = await waitReady(id, token);
      setUploadMsg("Ready.");
      await refreshDocs(token);
      await selectDoc(ready.id, token);
      await refreshUsage(token);
    } catch (err) {
      setUploadMsg(err instanceof Error ? err.message : "Upload failed");
      if (token) await refreshDocs(token).catch(() => {});
    }
  }

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !activeDocId) return;
    const q = askDraft.trim();
    if (!q) return;
    setAskDraft("");
    const userBubble: Bubble = { id: `u-${Date.now()}`, role: "user", content: q };
    const assistantId = `a-${Date.now()}`;
    setBubbles((b) => [...b, userBubble, { id: assistantId, role: "assistant", content: "" }]);
    setStatus("Streaming…");
    try {
      const res = await fetch(apiUrl("/ask/stream"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: q, document_id: activeDocId }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(errorMessage(err, "Ask failed"));
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No stream");
      const decoder = new TextDecoder();
      let buffer = "";
      let answer = "";
      let sources: Citation[] = [];
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const block of parts) {
          const lines = block.split("\n");
          let event = "message";
          let dataLine = "";
          for (const line of lines) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) dataLine += line.slice(5).trim();
          }
          if (!dataLine) continue;
          const payload = JSON.parse(dataLine);
          if (event === "meta") sources = payload.sources || [];
          if (event === "token") {
            answer += payload.token || "";
            setBubbles((bs) =>
              bs.map((b) => (b.id === assistantId ? { ...b, content: answer } : b))
            );
          }
          if (event === "done") {
            answer = payload.answer || answer;
            sources = payload.sources || sources;
            setBubbles((bs) =>
              bs.map((b) =>
                b.id === assistantId
                  ? {
                      ...b,
                      content: answer,
                      sources,
                      confidence: payload,
                    }
                  : b
              )
            );
          }
        }
      }
      await refreshUsage(token);
    } catch (err) {
      setBubbles((bs) =>
        bs.map((b) =>
          b.id === assistantId
            ? { ...b, content: `Error: ${err instanceof Error ? err.message : "Ask failed"}` }
            : b
        )
      );
    } finally {
      setStatus("Ready");
    }
  }

  async function logout() {
    try {
      if (token) await api("/auth/logout", { method: "POST", token });
    } catch {
      /* ignore */
    }
    setToken(null);
    setTok(null);
    setUser(null);
    setDocs([]);
    setActiveDocId(null);
  }

  if (booting) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-400">
        Loading Copilot…
      </div>
    );
  }

  if (!token || !user) {
    return <AuthPanel onAuthed={afterAuth} />;
  }

  const actions = personaActions(user.role);

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 flex flex-wrap items-center justify-between gap-3 border-b border-slate-700 bg-slate-950/90 px-4 py-3 backdrop-blur">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="font-display text-lg font-bold text-slate-50 hover:text-teal-300"
            onClick={() => setView("dashboard")}
          >
            AI Legal Copilot
          </button>
          <nav className="flex gap-1">
            <button
              type="button"
              onClick={() => setView("dashboard")}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                view === "dashboard"
                  ? "border border-slate-600 bg-teal-950/50 text-slate-50"
                  : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              Home
            </button>
            <button
              type="button"
              onClick={() =>
                goWorkspace({
                  hint: docs.length
                    ? "Select a document or upload another one."
                    : "Upload your first document to get started.",
                })
              }
              className={`rounded-lg px-3 py-1.5 text-sm ${
                view === "workspace"
                  ? "border border-slate-600 bg-teal-950/50 text-slate-50"
                  : "text-slate-400 hover:bg-slate-800"
              }`}
            >
              My documents
            </button>
          </nav>
          {user.role_label ? (
            <span className="rounded-full border border-teal-700/50 px-2 py-0.5 text-xs text-teal-300">
              {user.role_label}
            </span>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
          <span className="hidden md:inline">{usage}</span>
          <span className="hidden max-w-[180px] truncate sm:inline">{user.email}</span>
          {isAdmin ? (
            <Button
              size="sm"
              variant="ghost"
              onClick={async () => {
                setAdminOpen(true);
                setView("workspace");
                const stats = await api("/admin/stats", { token });
                setAdminStats(JSON.stringify(stats, null, 2));
              }}
            >
              Admin
            </Button>
          ) : null}
          <Button size="sm" variant="ghost" onClick={logout}>
            Sign out
          </Button>
        </div>
      </header>

      {view === "dashboard" ? (
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 lg:grid-cols-[1fr_280px]">
          <section>
            <p className="text-xs font-semibold uppercase tracking-[0.12em] text-amber-400/90">
              AI Legal Copilot
            </p>
            <h1 className="font-display mt-2 text-3xl font-bold text-slate-50 md:text-4xl">
              {user.full_name?.trim()
                ? `Welcome, ${user.full_name.trim()}`
                : "Welcome back"}
            </h1>
            <p className="mt-3 max-w-2xl text-slate-400 leading-relaxed">
              {user.welcome_message ||
                "Understand documents, explain contracts, detect risks, prepare for consultations, and connect with the right professionals."}
            </p>
            {!docs.length ? (
              <div className="mt-5 rounded-xl border border-amber-700/40 bg-gradient-to-br from-slate-800 to-slate-900 p-4">
                <h2 className="font-semibold text-slate-100">Get started in three steps</h2>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-slate-400">
                  <li>
                    <strong className="text-slate-200">Upload</strong> a contract or agreement
                  </li>
                  <li>
                    <strong className="text-slate-200">Ask</strong> for an explanation or risk scan
                  </li>
                  <li>
                    <strong className="text-slate-200">Prepare</strong> a briefing — then find the
                    right professional
                  </li>
                </ol>
              </div>
            ) : null}
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {actions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  onClick={() => handleAction(action)}
                  className="flex min-h-[132px] flex-col items-start gap-2 rounded-xl border border-slate-700 bg-gradient-to-br from-slate-800 to-slate-900 p-4 text-left transition hover:-translate-y-0.5 hover:border-teal-500"
                >
                  <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-amber-400/90">
                    {action.kicker}
                  </span>
                  <h2 className="text-lg font-semibold text-slate-50">{action.title}</h2>
                  <p className="flex-1 text-sm text-slate-400">{action.desc}</p>
                  <span className="text-sm font-medium text-teal-400">{action.go} →</span>
                </button>
              ))}
            </div>
          </section>
          <aside className="space-y-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/80 p-4">
              <h3 className="font-semibold text-slate-100">My documents</h3>
              <p className="mt-1 text-sm text-slate-400">
                {docs.length
                  ? `${docs.length} document${docs.length === 1 ? "" : "s"} · ${readyDocs.length} ready to review`
                  : "No documents yet."}
              </p>
              {!docs.length ? (
                <p className="mt-2 text-sm text-slate-500">
                  Upload your first agreement to unlock explanations, risk checks, and consultation
                  prep.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-slate-800">
                  {docs.slice(0, 5).map((d) => (
                    <li key={d.id}>
                      <button
                        type="button"
                        className="w-full py-2 text-left text-sm text-slate-300 hover:text-teal-300"
                        onClick={async () => {
                          goWorkspace({ hint: "Document selected from Home." });
                          await selectDoc(d.id);
                        }}
                      >
                        {docLabel(d)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <Button
                variant="primary"
                className="mt-3 w-full"
                onClick={() =>
                  goWorkspace({
                    hint: docs.length
                      ? "Select a document or upload another one."
                      : "Upload your first document to get started.",
                  })
                }
              >
                Open my documents
              </Button>
            </div>
            <div className="rounded-xl border-l-4 border-amber-500/70 bg-slate-800/70 px-3 py-2 text-xs leading-relaxed text-slate-400">
              Not legal advice. Answers are grounded in your documents and may be incomplete.
            </div>
          </aside>
        </div>
      ) : (
        <div className="grid min-h-[calc(100vh-57px)] lg:grid-cols-[280px_1fr]">
          <aside className="border-b border-slate-700 bg-slate-950/80 p-4 lg:border-b-0 lg:border-r">
            <Button size="sm" variant="ghost" onClick={() => setView("dashboard")}>
              ← Home
            </Button>
            <div className="mt-4">
              <h3 className="text-sm font-semibold text-slate-100">Add a document</h3>
              <p className="mt-1 text-xs text-slate-500">
                PDF or TXT. Processing stays private to your account.
              </p>
              <input
                type="file"
                accept=".pdf,.txt"
                className="mt-2 block w-full text-xs text-slate-400"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <Button variant="primary" className="mt-2 w-full" onClick={onUpload}>
                Upload & analyze
              </Button>
              <p className="mt-2 text-xs text-slate-500">{uploadMsg}</p>
            </div>
            <div className="mt-5">
              <h3 className="text-sm font-semibold text-slate-100">My documents</h3>
              {!docs.length ? (
                <p className="mt-2 text-sm text-slate-500">No documents yet.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {docs.map((d) => (
                    <li key={d.id}>
                      <button
                        type="button"
                        onClick={() => selectDoc(d.id)}
                        className={`w-full rounded-lg px-2 py-2 text-left text-sm ${
                          d.id === activeDocId
                            ? "border border-teal-600 bg-teal-950/40"
                            : "border border-transparent hover:bg-slate-800"
                        }`}
                      >
                        {docLabel(d)}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="mt-5 space-y-1">
              <p className="text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500">
                Understand
              </p>
              <Button variant="ghost" className="w-full justify-start" onClick={runExplain}>
                Explain this document
              </Button>
              <Button variant="ghost" className="w-full justify-start" onClick={runRisks}>
                Detect risks
              </Button>
              <p className="pt-2 text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500">
                Prepare & connect
              </p>
              <Button variant="ghost" className="w-full justify-start" onClick={runConsult}>
                Prepare for consultation
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => {
                  setExpert((e) => ({ ...e, open: true }));
                  runExpert();
                }}
              >
                Find a legal professional
              </Button>
              <p className="pt-2 text-[0.7rem] font-semibold uppercase tracking-wider text-slate-500">
                Conversation
              </p>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={async () => {
                  if (!token || !activeDocId) return;
                  await api(`/documents/${activeDocId}/conversation/reset`, {
                    method: "POST",
                    token,
                  });
                  setBubbles([]);
                }}
              >
                Clear conversation
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={async () => {
                  if (!token || !activeDocId) return;
                  const data = await api<{ content: string; filename?: string }>(
                    `/documents/${activeDocId}/export`,
                    { token }
                  );
                  const a = document.createElement("a");
                  a.href = URL.createObjectURL(
                    new Blob([data.content], { type: "text/plain" })
                  );
                  a.download = data.filename || "export.txt";
                  a.click();
                }}
              >
                Export notes
              </Button>
              <Button
                variant="danger"
                className="w-full justify-start"
                onClick={async () => {
                  if (!token || !activeDocId) return;
                  if (!confirm("Remove this document?")) return;
                  await api(`/documents/${activeDocId}`, { method: "DELETE", token });
                  setActiveDocId(null);
                  setBubbles([]);
                  await refreshDocs(token);
                }}
              >
                Remove document
              </Button>
            </div>
          </aside>

          <main className="flex min-h-0 flex-col">
            <div className="flex items-start justify-between gap-3 border-b border-slate-700 px-4 py-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-50">
                  {activeDoc?.original_filename || "Choose a document to get started"}
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  {activeDoc
                    ? "Ask a question, or use Explain / Detect risks / Prepare from the sidebar."
                    : "Upload or select a file, then ask questions or run a guided review."}
                </p>
              </div>
              <span className="rounded-full border border-slate-600 px-2 py-0.5 text-xs text-slate-400">
                {status}
              </span>
            </div>
            {hint ? (
              <div className="border-b border-slate-700 bg-teal-950/30 px-4 py-2 text-sm text-teal-300">
                {hint}
              </div>
            ) : null}

            {explain.open ? (
              <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 flex justify-between">
                  <h3 className="font-semibold">Document explanation</h3>
                  <Button size="sm" variant="ghost" onClick={() => setExplain((s) => ({ ...s, open: false }))}>
                    Close
                  </Button>
                </div>
                <p className="text-sm text-slate-400">{explain.status}</p>
                <ConfidenceBadge data={explain.confidence} />
                <div className="mt-3 space-y-3">
                  {explain.sections.map((s, i) => (
                    <div key={i} className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                      <h4 className="font-medium text-slate-100">{s.title}</h4>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-300">{s.content}</p>
                      <CiteChips citations={s.citations} />
                    </div>
                  ))}
                </div>
                {explain.disclaimer ? (
                  <p className="mt-3 text-xs text-slate-500">{explain.disclaimer}</p>
                ) : null}
              </section>
            ) : null}

            {risks.open ? (
              <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 flex justify-between">
                  <h3 className="font-semibold">Risk highlights</h3>
                  <Button size="sm" variant="ghost" onClick={() => setRisks((s) => ({ ...s, open: false }))}>
                    Close
                  </Button>
                </div>
                <p className="text-sm text-slate-400">{risks.status}</p>
                <div className="mt-3 space-y-3">
                  {risks.items.map((r, i) => (
                    <div key={i} className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                      <div className="flex justify-between gap-2">
                        <h4 className="font-medium">{r.title}</h4>
                        <span className="text-xs uppercase text-slate-400">
                          {r.evidence_found && r.severity ? r.severity : "No evidence"}
                        </span>
                      </div>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-300">
                        {r.explanation}
                      </p>
                      <CiteChips citations={r.citations} />
                    </div>
                  ))}
                </div>
                {risks.disclaimer ? (
                  <p className="mt-3 text-xs text-slate-500">{risks.disclaimer}</p>
                ) : null}
              </section>
            ) : null}

            {consult.open ? (
              <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 flex justify-between">
                  <h3 className="font-semibold">Consultation briefing</h3>
                  <Button size="sm" variant="ghost" onClick={() => setConsult((s) => ({ ...s, open: false }))}>
                    Close
                  </Button>
                </div>
                <p className="text-sm text-slate-400">{consult.status}</p>
                <div className="mt-3 space-y-3">
                  {consult.sections.map((s, i) => (
                    <div key={i} className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                      <h4 className="font-medium">{s.title}</h4>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-300">{s.content}</p>
                      <CiteChips citations={s.citations} />
                    </div>
                  ))}
                </div>
                <Button
                  variant="primary"
                  className="mt-3"
                  disabled={!consult.canPdf}
                  onClick={exportConsultPdf}
                >
                  Download PDF briefing
                </Button>
                {consult.disclaimer ? (
                  <p className="mt-3 text-xs text-slate-500">{consult.disclaimer}</p>
                ) : null}
              </section>
            ) : null}

            {expert.open ? (
              <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 flex justify-between">
                  <h3 className="font-semibold">Find the right legal professional</h3>
                  <Button size="sm" variant="ghost" onClick={() => setExpert((e) => ({ ...e, open: false }))}>
                    Close
                  </Button>
                </div>
                <p className="text-sm text-slate-400">{expert.status}</p>
                {expert.category ? (
                  <div className="mt-3 rounded-lg border border-slate-700 bg-slate-950 p-3">
                    <p className="text-xs uppercase text-slate-500">Recommended category</p>
                    <p className="text-xl font-semibold text-teal-400">{expert.category}</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-300">{expert.reason}</p>
                  </div>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button variant="primary" onClick={runExpert}>
                    Recommend expert category
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
                      setExpert((e) => ({ ...e, dirStatus: "Waiting for location permission…" }));
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
                <p className="mt-2 text-sm text-slate-500">{expert.dirStatus}</p>
                <div className="mt-3 space-y-2">
                  {expert.pros.map((p) => (
                    <div key={p.id} className="rounded-lg border border-slate-700 bg-slate-950 p-3">
                      <div className="flex justify-between gap-2">
                        <h5 className="font-medium">{p.name}</h5>
                        {p.verified ? (
                          <span className="text-xs text-emerald-400">Verified</span>
                        ) : null}
                      </div>
                      <p className="text-sm text-slate-300">{p.specialization}</p>
                      {p.distance_km != null ? (
                        <p className="text-sm text-teal-400">{p.distance_km.toFixed(1)} km</p>
                      ) : null}
                      <div className="mt-2 flex flex-wrap gap-2 text-xs">
                        {p.phone ? (
                          <a className="rounded border border-slate-600 px-2 py-1 text-teal-300" href={`tel:${p.phone}`}>
                            Call
                          </a>
                        ) : null}
                        {p.email ? (
                          <a className="rounded border border-slate-600 px-2 py-1 text-teal-300" href={`mailto:${p.email}`}>
                            Email
                          </a>
                        ) : null}
                        {p.website ? (
                          <a
                            className="rounded border border-slate-600 px-2 py-1 text-teal-300"
                            href={p.website}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Website
                          </a>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
                {expert.disclaimer ? (
                  <p className="mt-3 text-xs text-slate-500">{expert.disclaimer}</p>
                ) : null}
              </section>
            ) : null}

            <div ref={chatRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {activeDocId && !bubbles.length ? (
                <div className="mx-auto max-w-xl rounded-xl border border-dashed border-slate-600 bg-slate-900/50 p-6">
                  <h3 className="text-lg font-semibold text-slate-100">Ask your Copilot</h3>
                  <p className="mt-2 text-sm text-slate-400">
                    Try questions like “What are my payment obligations?” Answers include page
                    citations when available.
                  </p>
                </div>
              ) : null}
              {bubbles.map((b) => (
                <div
                  key={b.id}
                  className={`max-w-3xl whitespace-pre-wrap rounded-xl px-4 py-3 text-sm leading-relaxed ${
                    b.role === "user"
                      ? "ml-auto bg-slate-700 text-slate-50"
                      : "mr-auto border border-slate-700 bg-slate-900 text-slate-200"
                  }`}
                >
                  {b.content}
                  {b.sources?.length ? (
                    <div className="mt-2 text-xs text-slate-400">
                      {b.sources
                        .map(
                          (x) =>
                            `${x.filename || "doc"}${x.page != null ? ` p.${x.page}` : ""}`
                        )
                        .join(" · ")}
                    </div>
                  ) : null}
                  <ConfidenceBadge data={b.confidence} />
                </div>
              ))}
            </div>

            <form
              onSubmit={onAsk}
              className="flex gap-2 border-t border-slate-700 bg-slate-950/90 px-4 py-3"
            >
              <Input
                value={askDraft}
                onChange={(e) => setAskDraft(e.target.value)}
                placeholder="Ask about this document…"
                disabled={!activeDocId}
              />
              <Button type="submit" variant="primary" disabled={!activeDocId}>
                Ask
              </Button>
            </form>

            <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
              <h3 className="font-semibold">Compare contracts</h3>
              <p className="mt-1 text-sm text-slate-400">
                See how two agreements differ on payment, termination, liability, and other core
                terms.
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <select
                  className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm"
                  value={cmpA}
                  onChange={(e) => setCmpA(e.target.value)}
                >
                  <option value="">First document</option>
                  {readyDocs.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.original_filename}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-lg border border-slate-600 bg-slate-950 px-3 py-2 text-sm"
                  value={cmpB}
                  onChange={(e) => setCmpB(e.target.value)}
                >
                  <option value="">Second document</option>
                  {readyDocs.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.original_filename}
                    </option>
                  ))}
                </select>
              </div>
              <Input className="mt-2" value={cmpQ} onChange={(e) => setCmpQ(e.target.value)} />
              <Button
                className="mt-2"
                onClick={async () => {
                  if (!token || !cmpA || !cmpB || cmpA === cmpB) {
                    setCmpOut("Pick two different documents.");
                    return;
                  }
                  setCmpOut("Comparing…");
                  try {
                    const data = await api<{ answer: string } & Confidence>("/compare", {
                      method: "POST",
                      token,
                      json: {
                        document_id_a: cmpA,
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
              {cmpOut ? (
                <div className="mt-3 whitespace-pre-wrap text-sm text-slate-300">
                  {cmpOut}
                  <ConfidenceBadge data={cmpConf} />
                </div>
              ) : null}
            </section>

            {adminOpen ? (
              <section className="m-4 rounded-xl border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 flex justify-between">
                  <h3 className="font-semibold">Admin</h3>
                  <Button size="sm" variant="ghost" onClick={() => setAdminOpen(false)}>
                    Close
                  </Button>
                </div>
                <pre className="overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                  {adminStats}
                </pre>
              </section>
            ) : null}
          </main>
        </div>
      )}
    </div>
  );
}
