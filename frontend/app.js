const state = {
  token: localStorage.getItem("ldi_token") || null,
  user: null,
  docs: [],
  activeDocId: null,
  isAdmin: false,
  view: "dashboard", // dashboard | workspace
  lastConsultDocId: null,
  lastConsultExportName: null,
  recommendedCategory: null,
  userLocation: null, // { latitude, longitude } only after explicit permission
  directoryCity: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

/** Persona-specific home actions → existing workspace features */
const DASHBOARD_ACTIONS = {
  individual: [
    {
      id: "upload",
      kicker: "Start here",
      title: "Upload a legal document",
      desc: "Add a contract or agreement to your private workspace.",
      go: "Upload",
    },
    {
      id: "explain",
      kicker: "Understand",
      title: "Explain this contract",
      desc: "Plain-language parties, dates, obligations, and risks — with citations.",
      go: "Explain",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Highlight legal risks",
      desc: "Flag renewal, liability, penalties, and one-sided terms by severity.",
      go: "Scan risks",
    },
    {
      id: "ask",
      kicker: "Ask",
      title: "Ask your Copilot",
      desc: "Get cited answers about clauses, deadlines, and definitions.",
      go: "Ask now",
    },
    {
      id: "consult",
      kicker: "Prepare",
      title: "Prepare for a consultation",
      desc: "Build a briefing with facts, timeline, risks, and questions to ask.",
      go: "Prepare",
    },
    {
      id: "expert",
      kicker: "Connect",
      title: "Find the right professional",
      desc: "Get a category recommendation and browse curated directory matches.",
      go: "Find help",
    },
  ],
  lawyer: [
    {
      id: "upload",
      kicker: "Matter intake",
      title: "Upload client documents",
      desc: "Securely add client PDFs for review and cited Q&A.",
      go: "Upload",
    },
    {
      id: "explain",
      kicker: "Understand",
      title: "Explain this document",
      desc: "Structured overview with citations for rapid matter intake.",
      go: "Explain",
    },
    {
      id: "search",
      kicker: "Workspace",
      title: "Browse your matters",
      desc: "Jump between documents and ask targeted questions.",
      go: "Open files",
    },
    {
      id: "compare",
      kicker: "Compare",
      title: "Compare contracts",
      desc: "Diff two agreements on payment, liability, and exit terms.",
      go: "Compare",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Highlight legal risks",
      desc: "Severity-ranked risks with citations from the client document.",
      go: "Scan risks",
    },
    {
      id: "consult",
      kicker: "Prepare",
      title: "Prepare a consultation briefing",
      desc: "Hand clients a cited summary: facts, timeline, risks, questions.",
      go: "Prepare",
    },
    {
      id: "ask",
      kicker: "Ask",
      title: "Ask your Copilot",
      desc: "Cited answers grounded in the selected client document.",
      go: "Open assistant",
    },
  ],
  business_owner: [
    {
      id: "upload",
      kicker: "Start here",
      title: "Review a contract",
      desc: "Upload a deal document and review it with your Copilot.",
      go: "Upload",
    },
    {
      id: "explain",
      kicker: "Understand",
      title: "Explain this contract",
      desc: "Plain-language parties, obligations, risks, and deadlines.",
      go: "Explain",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Highlight legal risks",
      desc: "Auto-renewal, liability, penalties, and one-sided terms — cited.",
      go: "Scan risks",
    },
    {
      id: "consult",
      kicker: "Prepare",
      title: "Prepare for counsel",
      desc: "Walk into a consultation with a cited summary and questions.",
      go: "Prepare",
    },
    {
      id: "vendor",
      kicker: "Vendor deals",
      title: "Review vendor agreements",
      desc: "Focus on SLAs, payment, and termination terms.",
      go: "Review vendors",
      prompt: "Focus on vendor obligations, SLAs, payment terms, liability, and termination. Cite pages.",
    },
    {
      id: "employment",
      kicker: "People",
      title: "Review employment agreements",
      desc: "Check compensation, notice, and restrictive covenants.",
      go: "Review employment",
      prompt: "Analyze employment-related terms: role, compensation, notice, confidentiality, and non-compete. Cite pages.",
    },
    {
      id: "compliance",
      kicker: "Governance",
      title: "Check compliance language",
      desc: "Ask about audit, data, and regulatory clauses.",
      go: "Check compliance",
      prompt: "What compliance, audit, data protection, or regulatory obligations appear in this document? Cite pages.",
    },
  ],
  chartered_accountant: [
    {
      id: "upload",
      kicker: "Start here",
      title: "Upload a commercial agreement",
      desc: "Bring in contracts for financial and commercial review.",
      go: "Upload",
    },
    {
      id: "explain",
      kicker: "Understand",
      title: "Explain this document",
      desc: "Plain-language summary with parties, dates, and risks — cited.",
      go: "Explain",
    },
    {
      id: "understand",
      kicker: "Commercial",
      title: "Understand payment terms",
      desc: "Extract fees, schedules, and financial obligations.",
      go: "Analyze",
      prompt: "Extract all payment terms, fees, schedules, penalties, and financial obligations. Cite pages.",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Highlight commercial risks",
      desc: "Flag liability, penalties, renewal, and missing payment terms.",
      go: "Scan risks",
    },
    {
      id: "ask",
      kicker: "Ask",
      title: "Ask your Copilot",
      desc: "Query the document with citations for your notes.",
      go: "Ask now",
    },
  ],
  hr_professional: [
    {
      id: "upload",
      kicker: "Start here",
      title: "Upload an HR document",
      desc: "Add policies, offer letters, or vendor HR contracts.",
      go: "Upload",
    },
    {
      id: "employment",
      kicker: "Workforce",
      title: "Review employment agreements",
      desc: "Review notice, benefits, and restrictive terms.",
      go: "Review",
      prompt: "Summarize employment terms: duties, compensation, leave, notice, and post-employment restrictions. Cite pages.",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Highlight policy risks",
      desc: "Spot one-sided duties, confidentiality, and exit gaps.",
      go: "Scan risks",
    },
    {
      id: "ask",
      kicker: "Ask",
      title: "Ask your Copilot",
      desc: "Clarify policy language before you circulate it.",
      go: "Ask now",
    },
  ],
  student: [
    {
      id: "upload",
      kicker: "Learn",
      title: "Upload a legal document",
      desc: "Study real contracts with AI-guided explanations.",
      go: "Upload",
    },
    {
      id: "explain",
      kicker: "Understand",
      title: "Explain this document",
      desc: "Overview of type, parties, clauses, and risks — with citations.",
      go: "Explain",
    },
    {
      id: "risks",
      kicker: "Detect risks",
      title: "Practice spotting risks",
      desc: "Learn to recognize renewal, liability, and penalty clauses.",
      go: "Scan risks",
    },
    {
      id: "ask",
      kicker: "Ask",
      title: "Ask your Copilot",
      desc: "Test your understanding with cited answers.",
      go: "Ask now",
    },
    {
      id: "compare",
      kicker: "Compare",
      title: "Compare contracts",
      desc: "See how two agreements differ on core terms.",
      go: "Compare",
    },
  ],
};

function errorMessage(payload, fallback = "Request failed") {
  if (!payload) return fallback;
  if (payload.error?.message) return payload.error.message;
  const detail = payload.detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  if (detail && typeof detail === "object") {
    return detail.message || detail.code || fallback;
  }
  return detail || fallback;
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (opts.json) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
    delete opts.json;
  }
  const res = await fetch(path, { ...opts, headers });
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = { detail: text }; }
  if (!res.ok) {
    throw new Error(errorMessage(data, res.statusText));
  }
  return data;
}

function showAuth() {
  $("#view-auth").classList.remove("hidden");
  $("#view-app").classList.add("hidden");
}

function showApp() {
  $("#view-auth").classList.add("hidden");
  $("#view-app").classList.remove("hidden");
}

function setNavActive(view) {
  $$(".nav-link").forEach((el) => {
    el.classList.toggle("active", el.dataset.nav === view);
  });
}

function showDashboard() {
  state.view = "dashboard";
  $("#panel-dashboard").classList.remove("hidden");
  $("#panel-workspace").classList.add("hidden");
  setNavActive("dashboard");
  renderDashboard();
}

function showWorkspace(opts = {}) {
  state.view = "workspace";
  $("#panel-dashboard").classList.add("hidden");
  $("#panel-workspace").classList.remove("hidden");
  setNavActive("workspace");
  const hint = $("#intent-hint");
  const expert = $("#expert-panel");
  expert.classList.add("hidden");
  if (!opts.keepExplain) {
    $("#explain-panel")?.classList.add("hidden");
  }
  if (!opts.keepRisks) {
    $("#risks-panel")?.classList.add("hidden");
  }
  if (!opts.keepConsult) {
    $("#consult-panel")?.classList.add("hidden");
  }
  if (opts.hint) {
    hint.textContent = opts.hint;
    hint.classList.remove("hidden");
  } else {
    hint.classList.add("hidden");
  }
  if (opts.focusUpload) {
    setTimeout(() => $("#file-input")?.focus(), 50);
  }
  if (opts.focusAsk) {
    setTimeout(() => $("#ask-input")?.focus(), 80);
  }
  if (opts.focusCompare) {
    setTimeout(() => {
      $("#compare")?.scrollIntoView({ behavior: "smooth", block: "start" });
      $("#cmp-q")?.focus();
    }, 80);
  }
  if (opts.prompt) {
    $("#ask-input").value = opts.prompt;
    setTimeout(() => $("#ask-input")?.focus(), 80);
  }
  if (opts.showExpert) {
    expert.classList.remove("hidden");
    expert.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  updateChatEmptyState();
}

function setTab(name) {
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $("#form-login").classList.toggle("hidden", name !== "login");
  $("#form-register").classList.toggle("hidden", name !== "register");
  $("#form-forgot").classList.toggle("hidden", name !== "forgot");
}

$$(".tab").forEach((t) => t.addEventListener("click", () => setTab(t.dataset.tab)));

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  $("#login-error").textContent = "";
  try {
    const data = await api("/auth/login", {
      method: "POST",
      json: { email: fd.get("email"), password: fd.get("password") },
    });
    await afterAuth(data.access_token);
  } catch (err) {
    $("#login-error").textContent = err.message;
  }
});

$("#form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  $("#register-error").textContent = "";
  try {
    const role = fd.get("role");
    if (!role) {
      $("#register-error").textContent = "Please select your role.";
      return;
    }
    const data = await api("/auth/register", {
      method: "POST",
      json: {
        email: fd.get("email"),
        password: fd.get("password"),
        full_name: fd.get("full_name") || null,
        role,
        accept_disclaimer: true,
      },
    });
    await afterAuth(data.access_token);
  } catch (err) {
    $("#register-error").textContent = err.message;
  }
});

$("#form-forgot").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  try {
    await api("/auth/forgot-password", {
      method: "POST",
      json: { email: fd.get("email") },
    });
    $("#forgot-msg").textContent = "If that email exists, a reset was sent (check server logs in free/dev).";
  } catch (err) {
    $("#forgot-msg").textContent = err.message;
  }
});

$("#btn-reset").addEventListener("click", async () => {
  const fd = new FormData($("#form-forgot"));
  try {
    await api("/auth/reset-password", {
      method: "POST",
      json: { token: fd.get("token"), new_password: fd.get("new_password") },
    });
    $("#forgot-msg").textContent = "Password updated. Sign in.";
    setTab("login");
  } catch (err) {
    $("#forgot-msg").textContent = err.message;
  }
});

function personaActions(role) {
  return DASHBOARD_ACTIONS[role] || DASHBOARD_ACTIONS.individual;
}

function renderDashboard() {
  const user = state.user || {};
  const role = user.role || "individual";
  const name = (user.full_name || "").trim();
  const label = user.role_label || "Individual";

  $("#dash-eyebrow").textContent =
    role === "lawyer"
      ? "Counsel workspace"
      : role === "business_owner"
        ? "Business workspace"
        : "AI Legal Copilot";
  $("#dash-title").textContent = name
    ? `Welcome, ${name}`
    : `Welcome back`;
  $("#dash-subtitle").textContent =
    user.welcome_message ||
    "Understand documents, explain contracts, detect risks, prepare for consultations, and connect with the right professionals.";
  $("#topbar-role").textContent = label;

  const onboarding = $("#dash-onboarding");
  if (onboarding) {
    onboarding.classList.toggle("hidden", state.docs.length > 0);
  }

  const grid = $("#dash-actions");
  grid.innerHTML = "";
  personaActions(role).forEach((action) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "action-card";
    btn.setAttribute("role", "listitem");
    btn.dataset.action = action.id;
    btn.innerHTML = `
      <span class="action-kicker">${escapeHtml(action.kicker)}</span>
      <h2 class="action-title">${escapeHtml(action.title)}</h2>
      <p class="action-desc">${escapeHtml(action.desc)}</p>
      <span class="action-go">${escapeHtml(action.go)} →</span>
    `;
    btn.addEventListener("click", () => handleDashboardAction(action));
    grid.appendChild(btn);
  });

  const ready = state.docs.filter((d) => (d.status || "").toUpperCase() === "READY");
  const summary = $("#dash-doc-summary");
  const list = $("#dash-doc-list");
  const empty = $("#dash-doc-empty");
  list.innerHTML = "";
  if (!state.docs.length) {
    summary.textContent = "No documents yet.";
    empty?.classList.remove("hidden");
  } else {
    summary.textContent = `${state.docs.length} document${state.docs.length === 1 ? "" : "s"} · ${ready.length} ready to review`;
    empty?.classList.add("hidden");
    state.docs.slice(0, 5).forEach((d) => {
      const li = document.createElement("li");
      li.textContent = docStatusLabel(d);
      li.addEventListener("click", async () => {
        showWorkspace({ hint: "Document selected from Home." });
        await selectDoc(d.id);
      });
      list.appendChild(li);
    });
  }

  const uploadHeading = $("#upload-heading");
  if (uploadHeading) {
    uploadHeading.textContent =
      role === "lawyer" ? "Add a client document" : "Add a document";
  }
}

async function ensureReadyDocument() {
  const ready = state.docs.filter((d) => (d.status || "").toUpperCase() === "READY");
  if (!ready.length) return null;
  if (!state.activeDocId) {
    await selectDoc(ready[0].id);
    return ready[0];
  }
  const active = state.docs.find((d) => d.id === state.activeDocId);
  if (!active || (active.status || "").toUpperCase() !== "READY") {
    await selectDoc(ready[0].id);
    return ready[0];
  }
  return active;
}

function renderExplanation(data) {
  const panel = $("#explain-panel");
  const host = $("#explain-sections");
  const status = $("#explain-status");
  const disclaimer = $("#explain-disclaimer");
  panel.classList.remove("hidden");
  host.innerHTML = "";
  const confBit = data.confidence_level
    ? ` · ${confidenceLabel(data.confidence_level, data.confidence_score)}`
    : "";
  status.textContent = `Explanation for ${data.filename} · ${data.processing_time}s${confBit}`;
  disclaimer.textContent = data.disclaimer || "";
  attachConfidence(panel, data);

  (data.sections || []).forEach((sec) => {
    const el = document.createElement("article");
    el.className = `explain-section${sec.evidence_found ? "" : " missing"}`;
    const cites = (sec.citations || [])
      .map((c) => {
        const page = c.page != null ? ` p.${c.page}` : "";
        return `<span class="cite-chip" title="${escapeHtml(c.snippet || "")}">Source ${c.index}${page}</span>`;
      })
      .join("");
    el.innerHTML = `
      <h4>${escapeHtml(sec.title)}</h4>
      <p>${escapeHtml(sec.content)}</p>
      ${cites ? `<div class="explain-cites">${cites}</div>` : ""}
    `;
    host.appendChild(el);
  });
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runExplainDocument() {
  showWorkspace({
    keepExplain: true,
    hint: "Generating a grounded explanation from retrieved excerpts…",
  });
  const doc = await ensureReadyDocument();
  if (!doc) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload a document first — then Explain can run.",
    });
    return;
  }
  const panel = $("#explain-panel");
  const status = $("#explain-status");
  panel.classList.remove("hidden");
  $("#explain-sections").innerHTML = "";
  status.textContent = "Retrieving excerpts and generating explanation…";
  $("#explain-disclaimer").textContent = "";
  try {
    const data = await api("/explain", {
      method: "POST",
      json: { document_id: state.activeDocId },
    });
    renderExplanation(data);
    await refreshUsage();
    // Refresh chat so the persisted explanation appears
    if (state.activeDocId) await selectDoc(state.activeDocId);
  } catch (err) {
    status.textContent = `Could not explain document: ${err.message}`;
  }
}

function renderRiskHighlights(data) {
  const panel = $("#risks-panel");
  const host = $("#risks-list");
  const status = $("#risks-status");
  const disclaimer = $("#risks-disclaimer");
  panel.classList.remove("hidden");
  host.innerHTML = "";
  const flagged = data.flagged_count ?? (data.risks || []).filter((r) => r.evidence_found).length;
  const confBit = data.confidence_level
    ? ` · ${confidenceLabel(data.confidence_level, data.confidence_score)}`
    : "";
  status.textContent = `Risk scan for ${data.filename} · ${flagged} flagged · ${data.processing_time}s${confBit}`;
  disclaimer.textContent = data.disclaimer || "";
  attachConfidence(panel, data);

  (data.risks || []).forEach((risk) => {
    const el = document.createElement("article");
    el.className = `risk-card${risk.evidence_found ? "" : " missing"}`;
    const sev = (risk.severity || "").toLowerCase();
    const sevLabel = risk.evidence_found && risk.severity ? risk.severity : "No evidence";
    const sevClass = risk.evidence_found && sev ? sev : "none";
    const cites = (risk.citations || [])
      .map((c) => {
        const page = c.page != null ? ` p.${c.page}` : "";
        return `<span class="cite-chip" title="${escapeHtml(c.snippet || "")}">Source ${c.index}${page}</span>`;
      })
      .join("");
    el.innerHTML = `
      <div class="risk-card-top">
        <h4>${escapeHtml(risk.title)}</h4>
        <span class="risk-severity ${sevClass}">${escapeHtml(sevLabel)}</span>
      </div>
      <p>${escapeHtml(risk.explanation)}</p>
      ${cites ? `<div class="risk-cites">${cites}</div>` : ""}
    `;
    host.appendChild(el);
  });
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function formatDistance(km) {
  if (km == null || Number.isNaN(Number(km))) return "Distance unavailable";
  const n = Number(km);
  if (n < 1) return `${Math.round(n * 1000)} m away`;
  return `${n.toFixed(n < 10 ? 1 : 0)} km away`;
}

function renderProfessionalCards(host, professionals) {
  host.innerHTML = "";
  (professionals || []).forEach((p) => {
    const el = document.createElement("article");
    el.className = "pro-card";
    const practice = p.practice_area || p.specialization || "—";
    const loc = [p.city, p.state, p.country].filter(Boolean).join(", ");
    const call = p.phone
      ? `<a href="tel:${escapeHtml(p.phone)}">Call</a>`
      : `<span class="pro-action-disabled">Call</span>`;
    const email = p.email
      ? `<a href="mailto:${escapeHtml(p.email)}">Email</a>`
      : `<span class="pro-action-disabled">Email</span>`;
    let website = `<span class="pro-action-disabled">Website</span>`;
    if (p.website) {
      const href = /^https?:\/\//i.test(p.website) ? p.website : `https://${p.website}`;
      website = `<a href="${escapeHtml(href)}" target="_blank" rel="noopener">Website</a>`;
    }
    el.innerHTML = `
      <div class="pro-card-top">
        <h5>${escapeHtml(p.name)}</h5>
        ${p.verified ? `<span class="pro-verified">Verified</span>` : ""}
      </div>
      <p class="pro-practice"><strong>Practice Area:</strong> ${escapeHtml(practice)}</p>
      <p class="pro-distance">${escapeHtml(formatDistance(p.distance_km))}</p>
      ${loc ? `<p class="pro-meta">${escapeHtml(loc)}</p>` : ""}
      <div class="pro-actions">${call}${email}${website}</div>
    `;
    host.appendChild(el);
  });
}

async function fetchRecommendedProfessionals() {
  const wrap = $("#expert-directory");
  const status = $("#expert-directory-status");
  const list = $("#expert-directory-list");
  const category = state.recommendedCategory;
  if (!wrap) return;
  wrap.classList.remove("hidden");
  list.innerHTML = "";

  const params = new URLSearchParams();
  if (category) params.set("specialization", category);
  if (state.userLocation) {
    params.set("latitude", String(state.userLocation.latitude));
    params.set("longitude", String(state.userLocation.longitude));
  }
  if (state.directoryCity) params.set("city", state.directoryCity);

  if (!category && !state.userLocation && !state.directoryCity) {
    status.textContent =
      "Choose Use my location (permission required) or search by city to see nearby professionals.";
    return;
  }

  const mode = state.userLocation
    ? "near your location"
    : state.directoryCity
      ? `in ${state.directoryCity}`
      : "for this category";
  status.textContent = `Finding professionals ${mode}…`;

  try {
    const pros = await api(`/professionals/recommend?${params.toString()}`);
    if (!pros.length) {
      status.textContent = state.userLocation
        ? "No nearby directory profiles found. Try a city search, or ask an admin to add professionals with coordinates."
        : state.directoryCity
          ? `No directory profiles found in “${state.directoryCity}”.`
          : `No directory profiles for “${category}” yet. Try a city search or ask an admin to add some.`;
      return;
    }
    const sortHint = state.userLocation
      ? "Sorted by distance, then specialization match, then verification."
      : "Sorted by city match / specialization match, then verification.";
    status.textContent = `${pros.length} match${pros.length === 1 ? "" : "es"} ${mode}. ${sortHint}`;
    renderProfessionalCards(list, pros);
  } catch (err) {
    status.textContent = `Could not load directory: ${err.message}`;
  }
}

function requestUserLocation() {
  const status = $("#expert-directory-status");
  if (!navigator.geolocation) {
    if (status) {
      status.textContent =
        "Location is not supported in this browser. Search by city instead.";
    }
    return;
  }
  if (status) {
    status.textContent = "Waiting for location permission…";
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      state.userLocation = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
      };
      // Location takes priority over city filter for near-me ranking.
      fetchRecommendedProfessionals();
    },
    (err) => {
      state.userLocation = null;
      if (status) {
        status.textContent =
          err.code === 1
            ? "Location permission denied. You can still search by city."
            : "Could not get your location. Search by city instead.";
      }
    },
    { enableHighAccuracy: false, timeout: 12000, maximumAge: 60000 }
  );
}

async function loadProfessionalsForCategory(category) {
  state.recommendedCategory = category || null;
  // Do not auto-request location — wait for explicit user action.
  await fetchRecommendedProfessionals();
}

function renderExpertRecommendation(data) {
  const panel = $("#expert-panel");
  const result = $("#expert-result");
  const status = $("#expert-status");
  panel.classList.remove("hidden");
  result.classList.remove("hidden");
  status.textContent = `Recommendation for ${data.filename} · ${data.processing_time}s`;
  $("#expert-category").textContent = data.category || "—";
  $("#expert-reason").textContent = data.reason || "";
  $("#expert-disclaimer").textContent = data.disclaimer || "";
  const based = data.based_on || {};
  const parts = [];
  if (based.document) parts.push("document");
  if (based.questions) parts.push("your questions");
  if (based.risks) parts.push("detected risks");
  const riskBit =
    data.detected_risks?.length
      ? ` Risks considered: ${data.detected_risks.join(", ")}.`
      : "";
  $("#expert-signals").textContent = parts.length
    ? `Based on: ${parts.join(", ")}.${riskBit}`
    : `Based on limited signals.${riskBit}`;
  if (data.category) {
    loadProfessionalsForCategory(data.category);
  } else {
    $("#expert-directory")?.classList.add("hidden");
  }
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderConsultationPrep(data) {
  const panel = $("#consult-panel");
  const host = $("#consult-sections");
  const status = $("#consult-status");
  const disclaimer = $("#consult-disclaimer");
  panel.classList.remove("hidden");
  host.innerHTML = "";
  status.textContent = `Consultation prep for ${data.filename} · ${data.processing_time}s`;
  disclaimer.textContent = data.disclaimer || "";
  state.lastConsultDocId = data.document_id;
  state.lastConsultExportName = data.export_filename || "consultation_prep.pdf";
  const pdfBtn = $("#btn-consult-pdf");
  if (pdfBtn) pdfBtn.disabled = false;

  (data.sections || []).forEach((sec) => {
    const el = document.createElement("article");
    el.className = `consult-section${sec.evidence_found ? "" : " missing"}`;
    const cites = (sec.citations || [])
      .map((c) => {
        const page = c.page != null ? ` p.${c.page}` : "";
        return `<span class="cite-chip" title="${escapeHtml(c.snippet || "")}">Source ${c.index}${page}</span>`;
      })
      .join("");
    el.innerHTML = `
      <h4>${escapeHtml(sec.title)}</h4>
      <p>${escapeHtml(sec.content)}</p>
      ${cites ? `<div class="consult-cites">${cites}</div>` : ""}
    `;
    host.appendChild(el);
  });
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function runPrepareConsultation() {
  showWorkspace({
    keepConsult: true,
    hint: "Preparing a cited consultation briefing from your document…",
  });
  const doc = await ensureReadyDocument();
  if (!doc) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload a document first — then Prepare for consultation can run.",
    });
    return;
  }
  const panel = $("#consult-panel");
  const status = $("#consult-status");
  panel.classList.remove("hidden");
  $("#consult-sections").innerHTML = "";
  status.textContent = "Retrieving excerpts and building your briefing…";
  $("#consult-disclaimer").textContent = "";
  const pdfBtn = $("#btn-consult-pdf");
  if (pdfBtn) pdfBtn.disabled = true;
  try {
    const data = await api("/prepare-consultation", {
      method: "POST",
      json: { document_id: state.activeDocId },
    });
    renderConsultationPrep(data);
    await refreshUsage();
    if (state.activeDocId) await selectDoc(state.activeDocId);
  } catch (err) {
    status.textContent = `Could not prepare consultation briefing: ${err.message}`;
  }
}

async function exportConsultationPdf() {
  const docId = state.lastConsultDocId || state.activeDocId;
  if (!docId) return;
  const status = $("#consult-status");
  const prev = status?.textContent || "";
  if (status) status.textContent = "Generating PDF…";
  try {
    const res = await fetch("/prepare-consultation/pdf", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.token}`,
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
    a.download = state.lastConsultExportName || "consultation_prep.pdf";
    a.click();
    URL.revokeObjectURL(a.href);
    if (status) status.textContent = prev || "PDF downloaded.";
    await refreshUsage();
  } catch (err) {
    if (status) status.textContent = `PDF export failed: ${err.message}`;
  }
}

async function runRecommendExpert() {
  showWorkspace({
    showExpert: true,
    hint: "Recommending an expert category from your document, questions, and risks…",
  });
  const doc = await ensureReadyDocument();
  if (!doc) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload a document first — then we can recommend a professional category.",
    });
    return;
  }
  const panel = $("#expert-panel");
  const status = $("#expert-status");
  panel.classList.remove("hidden");
  $("#expert-result").classList.add("hidden");
  $("#expert-directory")?.classList.add("hidden");
  status.textContent = "Analyzing document, questions, and risk signals…";
  $("#expert-disclaimer").textContent = "";
  try {
    const data = await api("/recommend-expert", {
      method: "POST",
      json: { document_id: state.activeDocId },
    });
    renderExpertRecommendation(data);
    await refreshUsage();
    if (state.activeDocId) await selectDoc(state.activeDocId);
  } catch (err) {
    status.textContent = `Could not recommend an expert category: ${err.message}`;
  }
}

async function runHighlightRisks() {
  showWorkspace({
    keepRisks: true,
    hint: "Scanning retrieved excerpts for common legal risks…",
  });
  const doc = await ensureReadyDocument();
  if (!doc) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload a document first — then Detect risks can run.",
    });
    return;
  }
  const panel = $("#risks-panel");
  const status = $("#risks-status");
  panel.classList.remove("hidden");
  $("#risks-list").innerHTML = "";
  status.textContent = "Retrieving excerpts and analyzing risks…";
  $("#risks-disclaimer").textContent = "";
  try {
    const data = await api("/risks", {
      method: "POST",
      json: { document_id: state.activeDocId },
    });
    renderRiskHighlights(data);
    await refreshUsage();
    if (state.activeDocId) await selectDoc(state.activeDocId);
  } catch (err) {
    status.textContent = `Could not highlight risks: ${err.message}`;
  }
}

async function handleDashboardAction(action) {
  const needsDoc = ["understand", "ask", "vendor", "employment", "compliance", "explain"].includes(
    action.id
  );
  const ready = state.docs.filter((d) => (d.status || "").toUpperCase() === "READY");

  if (action.id === "upload") {
    showWorkspace({
      focusUpload: true,
      hint: "Choose a PDF or TXT to upload. Analysis runs in the background.",
    });
    return;
  }

  if (action.id === "search") {
    showWorkspace({
      hint: "Select a document in the sidebar, then ask questions across your files.",
    });
    return;
  }

  if (action.id === "compare") {
    showWorkspace({
      focusCompare: true,
      hint: "Pick two ready documents and run a comparison.",
    });
    return;
  }

  if (action.id === "expert") {
    await runRecommendExpert();
    return;
  }

  if (action.id === "explain") {
    await runExplainDocument();
    return;
  }

  if (action.id === "risks") {
    await runHighlightRisks();
    return;
  }

  if (action.id === "consult") {
    await runPrepareConsultation();
    return;
  }

  if (needsDoc && !ready.length) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload a document first — then this action can use it.",
    });
    return;
  }

  await ensureReadyDocument();

  showWorkspace({
    prompt: action.prompt || "",
    focusAsk: true,
    hint: action.title,
  });
}

async function afterAuth(token) {
  state.token = token;
  localStorage.setItem("ldi_token", token);
  state.user = await api("/auth/me");
  $("#user-email").textContent = state.user.email;
  const roleEl = $("#user-role");
  if (roleEl) roleEl.textContent = state.user.role_label || "";
  const banner = $("#welcome-banner");
  if (banner) {
    banner.textContent = state.user.welcome_message || "";
  }
  showApp();
  await refreshDocs();
  await refreshUsage();
  await probeAdmin();
  showDashboard();
}

async function probeAdmin() {
  try {
    await api("/admin/stats");
    state.isAdmin = true;
    $("#btn-admin").classList.remove("hidden");
  } catch {
    state.isAdmin = false;
    $("#btn-admin").classList.add("hidden");
  }
}

async function refreshUsage() {
  try {
    const u = await api("/account/usage");
    $("#usage").textContent =
      `Questions ${u.questions_last_hour}/${u.questions_limit} · ` +
      `Uploads ${u.uploads_last_hour}/${u.uploads_limit} · ` +
      `Documents ${u.documents_owned}/${u.documents_limit}`;
  } catch {
    $("#usage").textContent = "";
  }
}

function docStatusLabel(d) {
  const status = (d.status || "").toUpperCase();
  if (status === "READY") return `${d.original_filename} · Ready`;
  if (status === "FAILED") return `${d.original_filename} · Failed`;
  if (status === "PROCESSING" || status === "UPLOADING") {
    return `${d.original_filename} · Processing…`;
  }
  return `${d.original_filename} · ${status || "Processing…"}`;
}

function updateChatEmptyState() {
  const chat = $("#chat");
  const empty = $("#chat-empty");
  if (!chat || !empty) return;
  const hasBubbles = chat.querySelector(".bubble");
  const hasDoc = Boolean(state.activeDocId);
  empty.classList.toggle("hidden", Boolean(hasBubbles) || !hasDoc);
  chat.classList.toggle("chat-has-empty", !hasBubbles && hasDoc);
}

async function refreshDocs() {
  state.docs = await api("/documents");
  const list = $("#doc-list");
  const empty = $("#doc-list-empty");
  if (list) {
    list.innerHTML = "";
    state.docs.forEach((d) => {
      const li = document.createElement("li");
      li.textContent = docStatusLabel(d);
      li.dataset.id = d.id;
      if (d.id === state.activeDocId) li.classList.add("active");
      li.addEventListener("click", () => selectDoc(d.id));
      list.appendChild(li);
    });
  }
  if (empty) empty.classList.toggle("hidden", state.docs.length > 0);
  fillCompareSelects();
  if (!state.activeDocId && state.docs[0]) {
    const ready = state.docs.find((d) => (d.status || "").toUpperCase() === "READY");
    if (ready && state.view === "workspace") await selectDoc(ready.id);
  }
  if (state.view === "dashboard") renderDashboard();
  if (!state.activeDocId) {
    const title = $("#active-doc-title");
    const hint = $("#active-doc-hint");
    if (title) title.textContent = "Choose a document to get started";
    if (hint) {
      hint.textContent = state.docs.length
        ? "Select a file from the sidebar, or upload a new one."
        : "Upload a contract or agreement to begin.";
      hint.classList.remove("hidden");
    }
    updateChatEmptyState();
  }
}

function fillCompareSelects() {
  const ready = state.docs.filter((d) => (d.status || "").toUpperCase() === "READY");
  for (const id of ["cmp-a", "cmp-b"]) {
    const sel = $(`#${id}`);
    if (!sel) continue;
    sel.innerHTML = ready
      .map((d) => `<option value="${d.id}">${escapeHtml(d.original_filename)}</option>`)
      .join("");
    if (ready[1] && id === "cmp-b") sel.selectedIndex = 1;
  }
}

async function waitForDocumentReady(documentId, { timeoutMs = 120000, intervalMs = 1000 } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const doc = await api(`/documents/${documentId}`);
    const status = (doc.status || "").toUpperCase();
    if (status === "READY") return doc;
    if (status === "FAILED") {
      throw new Error(doc.processing_error || "Document processing failed");
    }
    $("#upload-msg").textContent = `Processing… (${status})`;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error("Timed out waiting for document processing");
}

async function selectDoc(id) {
  state.activeDocId = id;
  const doc = state.docs.find((d) => d.id === id);
  $("#active-doc-title").textContent = doc ? doc.original_filename : "Document";
  const headerHint = $("#active-doc-hint");
  if (headerHint) {
    headerHint.textContent = "Ask a question, or use Explain / Detect risks / Prepare from the sidebar.";
    headerHint.classList.remove("hidden");
  }
  $$("#doc-list li").forEach((li) => li.classList.toggle("active", li.dataset.id === id));
  const messages = await api(`/documents/${id}/messages`);
  const chat = $("#chat");
  chat.innerHTML = "";
  messages.forEach((m) => appendBubble(m.role, m.content));
  updateChatEmptyState();
}

function confidenceLabel(level, score) {
  if (!level) return "";
  const scoreBit = score != null && !Number.isNaN(Number(score)) ? ` · ${Number(score).toFixed(2)}` : "";
  return `Confidence: ${level}${scoreBit}`;
}

function attachConfidence(host, data) {
  if (!host || !data?.confidence_level) return;
  host.querySelector(".confidence-badge")?.remove();
  host.querySelector(".confidence-note")?.remove();
  const badge = document.createElement("div");
  const level = String(data.confidence_level);
  badge.className = `confidence-badge ${level.toLowerCase()}`;
  badge.textContent = confidenceLabel(level, data.confidence_score);
  host.appendChild(badge);
  if (data.recommendation) {
    const note = document.createElement("div");
    note.className = "confidence-note";
    note.textContent = data.recommendation;
    host.appendChild(note);
  }
}

function appendBubble(role, content, sources, confidence) {
  const div = document.createElement("div");
  div.className = `bubble ${role}`;
  div.textContent = content;
  if (sources?.length) {
    const s = document.createElement("div");
    s.className = "sources";
    s.textContent = sources
      .map((x) => {
        const page = x.page != null ? ` p.${x.page}` : "";
        return `${x.filename || "doc"}${page}`;
      })
      .join(" · ");
    div.appendChild(s);
  }
  if (confidence) attachConfidence(div, confidence);
  $("#chat").appendChild(div);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  updateChatEmptyState();
  return div;
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

$("#btn-home").addEventListener("click", () => showDashboard());
$("#nav-home")?.addEventListener("click", () => showDashboard());
$("#nav-docs")?.addEventListener("click", () =>
  showWorkspace({
    hint: state.docs.length
      ? "Select a document or upload another one."
      : "Upload your first document to get started.",
  })
);
$("#btn-back-dashboard").addEventListener("click", () => showDashboard());
$("#btn-open-workspace").addEventListener("click", () =>
  showWorkspace({
    hint: state.docs.length
      ? "Select a document or upload another one."
      : "Upload your first document to get started.",
  })
);
$("#btn-explain-close")?.addEventListener("click", () => {
  $("#explain-panel").classList.add("hidden");
});
$("#btn-explain-doc")?.addEventListener("click", () => runExplainDocument());
$("#btn-risks-close")?.addEventListener("click", () => {
  $("#risks-panel").classList.add("hidden");
});
$("#btn-risks-doc")?.addEventListener("click", () => runHighlightRisks());
$("#btn-consult-close")?.addEventListener("click", () => {
  $("#consult-panel").classList.add("hidden");
});
$("#btn-consult-doc")?.addEventListener("click", () => runPrepareConsultation());
$("#btn-consult-pdf")?.addEventListener("click", () => exportConsultationPdf());

$("#btn-expert-close")?.addEventListener("click", () => {
  $("#expert-panel").classList.add("hidden");
});
$("#btn-expert-doc")?.addEventListener("click", () => runRecommendExpert());
$("#btn-expert-recommend")?.addEventListener("click", () => runRecommendExpert());
$("#btn-use-location")?.addEventListener("click", () => requestUserLocation());
$("#form-city-search")?.addEventListener("submit", (e) => {
  e.preventDefault();
  const city = ($("#directory-city")?.value || "").trim();
  state.directoryCity = city || null;
  if (!city && !state.userLocation && !state.recommendedCategory) {
    const status = $("#expert-directory-status");
    if (status) status.textContent = "Enter a city to search.";
    return;
  }
  fetchRecommendedProfessionals();
});
$("#btn-expert-export")?.addEventListener("click", async () => {
  if (!state.activeDocId) {
    showWorkspace({
      focusUpload: true,
      hint: "Upload and select a document first, then export prep notes.",
    });
    return;
  }
  const data = await api(`/documents/${state.activeDocId}/export`);
  const blob = new Blob([data.content], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = data.filename || "legal-prep-notes.txt";
  a.click();
});

$("#btn-upload").addEventListener("click", async () => {
  const file = $("#file-input").files?.[0];
  if (!file) {
    $("#upload-msg").textContent = "Choose a PDF or TXT first.";
    return;
  }
  $("#upload-msg").textContent = "Processing…";
  $("#btn-upload").disabled = true;
  try {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/documents/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${state.token}` },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(errorMessage(data, "Upload failed"));
    $("#upload-msg").textContent = "Uploaded. Processing…";
    await refreshDocs();
    const ready = await waitForDocumentReady(data.document.id);
    $("#upload-msg").textContent = "Ready.";
    await refreshDocs();
    await selectDoc(ready.id);
    await refreshUsage();
  } catch (err) {
    $("#upload-msg").textContent = err.message;
    await refreshDocs().catch(() => {});
  } finally {
    $("#btn-upload").disabled = false;
  }
});

$("#form-ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!state.activeDocId) return;
  const q = $("#ask-input").value.trim();
  if (!q) return;
  $("#ask-input").value = "";
  appendBubble("user", q);
  const bubble = appendBubble("assistant", "");
  $("#status-pill").textContent = "Streaming…";
  let sources = [];
  try {
    const res = await fetch("/ask/stream", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${state.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: q, document_id: state.activeDocId }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(errorMessage(err, "Ask failed"));
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let answer = "";
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
          bubble.textContent = answer;
          $("#chat").scrollTop = $("#chat").scrollHeight;
        }
        if (event === "done") {
          answer = payload.answer || answer;
          sources = payload.sources || sources;
          bubble.textContent = answer;
          if (sources.length) {
            const s = document.createElement("div");
            s.className = "sources";
            s.textContent = sources
              .map((x) => `${x.filename || "doc"}${x.page != null ? ` p.${x.page}` : ""}`)
              .join(" · ");
            bubble.appendChild(s);
          }
          attachConfidence(bubble, payload);
        }
      }
    }
    await refreshUsage();
  } catch (err) {
    bubble.textContent = `Error: ${err.message}`;
  } finally {
    $("#status-pill").textContent = "Ready";
  }
});

$("#btn-compare").addEventListener("click", async () => {
  const a = $("#cmp-a").value;
  const b = $("#cmp-b").value;
  if (!a || !b || a === b) {
    $("#cmp-out").textContent = "Pick two different documents.";
    return;
  }
  $("#cmp-out").textContent = "Comparing…";
  try {
    const data = await api("/compare", {
      method: "POST",
      json: { document_id_a: a, document_id_b: b, question: $("#cmp-q").value },
    });
    const out = $("#cmp-out");
    out.textContent = data.answer;
    attachConfidence(out, data);
  } catch (err) {
    $("#cmp-out").textContent = err.message;
  }
});

$("#btn-reset-chat").addEventListener("click", async () => {
  if (!state.activeDocId) return;
  await api(`/documents/${state.activeDocId}/conversation/reset`, { method: "POST" });
  $("#chat").innerHTML = "";
});

$("#btn-export").addEventListener("click", async () => {
  if (!state.activeDocId) return;
  const data = await api(`/documents/${state.activeDocId}/export`);
  const blob = new Blob([data.content], { type: "text/plain" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = data.filename || "export.txt";
  a.click();
});

$("#btn-delete-doc").addEventListener("click", async () => {
  if (!state.activeDocId) return;
  if (!confirm("Delete this document and its chat?")) return;
  await api(`/documents/${state.activeDocId}`, { method: "DELETE" });
  state.activeDocId = null;
  $("#chat").innerHTML = "";
  await refreshDocs();
});

$("#btn-logout").addEventListener("click", async () => {
  try {
    if (state.token) await api("/auth/logout", { method: "POST" });
  } catch {
    /* ignore */
  }
  state.token = null;
  localStorage.removeItem("ldi_token");
  showAuth();
});

async function refreshAdminProfessionals() {
  const host = $("#admin-professionals");
  if (!host) return;
  const pros = await api("/admin/professionals");
  if (!pros.length) {
    host.innerHTML = `<p class="muted">No professionals yet.</p>`;
    return;
  }
  host.innerHTML =
    `<table><thead><tr><th>Name</th><th>Specialization</th><th>City</th><th>Verified</th><th></th></tr></thead><tbody>` +
    pros
      .map(
        (p) => `<tr>
      <td>${escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.specialization)}</td>
      <td>${escapeHtml(p.city)}</td>
      <td>${p.verified ? "yes" : "no"}</td>
      <td><button data-del-pro="${p.id}" class="btn" type="button">Delete</button></td>
    </tr>`
      )
      .join("") +
    `</tbody></table>`;
  host.onclick = async (ev) => {
    const id = ev.target.getAttribute("data-del-pro");
    if (!id) return;
    if (!confirm("Delete this professional?")) return;
    await api(`/admin/professionals/${id}`, { method: "DELETE" });
    await refreshAdminProfessionals();
  };
}

$("#btn-admin").addEventListener("click", async () => {
  showWorkspace();
  const panel = $("#admin-panel");
  panel.classList.toggle("hidden");
  if (panel.classList.contains("hidden")) return;
  const stats = await api("/admin/stats");
  $("#admin-stats").textContent = JSON.stringify(stats, null, 2);
  const users = await api("/admin/users");
  $("#admin-users").innerHTML =
    `<table><thead><tr><th>Email</th><th>Role</th><th>Plan</th><th>Docs</th><th>Active</th><th></th></tr></thead><tbody>` +
    users
      .map(
        (u) => `<tr>
      <td>${escapeHtml(u.email)}</td>
      <td>${escapeHtml(u.role || "individual")}</td>
      <td>${escapeHtml(u.plan)}</td>
      <td>${u.document_count}</td>
      <td>${u.is_active}</td>
      <td>${
        u.is_active
          ? `<button data-disable="${u.id}" class="btn">Disable</button>`
          : `<button data-enable="${u.id}" class="btn">Enable</button>`
      }</td>
    </tr>`
      )
      .join("") +
    `</tbody></table>`;
  $("#admin-users").onclick = async (ev) => {
    const dis = ev.target.getAttribute("data-disable");
    const en = ev.target.getAttribute("data-enable");
    if (dis) await api(`/admin/users/${dis}/disable`, { method: "POST" });
    if (en) await api(`/admin/users/${en}/enable`, { method: "POST" });
    if (dis || en) $("#btn-admin").click(), $("#btn-admin").click();
  };
  try {
    const cats = await api("/admin/professionals/categories");
    const sel = $("#admin-pro-spec");
    if (sel) {
      sel.innerHTML = (cats.categories || [])
        .map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
        .join("");
    }
    await refreshAdminProfessionals();
  } catch (err) {
    const msg = $("#admin-pro-msg");
    if (msg) msg.textContent = err.message;
  }
});

$("#form-admin-professional")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const msg = $("#admin-pro-msg");
  const lat = fd.get("latitude");
  const lng = fd.get("longitude");
  const payload = {
    name: fd.get("name"),
    specialization: fd.get("specialization"),
    city: fd.get("city"),
    state: fd.get("state") || "",
    country: fd.get("country") || "",
    phone: fd.get("phone") || null,
    email: fd.get("email") || null,
    website: fd.get("website") || null,
    latitude: lat === "" || lat == null ? null : Number(lat),
    longitude: lng === "" || lng == null ? null : Number(lng),
    verified: fd.get("verified") === "on",
  };
  try {
    await api("/admin/professionals", { method: "POST", json: payload });
    if (msg) msg.textContent = "Professional added.";
    e.target.reset();
    await refreshAdminProfessionals();
  } catch (err) {
    if (msg) msg.textContent = err.message;
  }
});

(async function boot() {
  if (!state.token) {
    showAuth();
    return;
  }
  try {
    await afterAuth(state.token);
  } catch {
    localStorage.removeItem("ldi_token");
    state.token = null;
    showAuth();
  }
})();
