import type { DashboardAction } from "./types";

export const DASHBOARD_ACTIONS: Record<string, DashboardAction[]> = {
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
      prompt:
        "Focus on vendor obligations, SLAs, payment terms, liability, and termination. Cite pages.",
    },
    {
      id: "employment",
      kicker: "People",
      title: "Review employment agreements",
      desc: "Check compensation, notice, and restrictive covenants.",
      go: "Review employment",
      prompt:
        "Analyze employment-related terms: role, compensation, notice, confidentiality, and non-compete. Cite pages.",
    },
    {
      id: "compliance",
      kicker: "Governance",
      title: "Check compliance language",
      desc: "Ask about audit, data, and regulatory clauses.",
      go: "Check compliance",
      prompt:
        "What compliance, audit, data protection, or regulatory obligations appear in this document? Cite pages.",
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
      prompt:
        "Extract all payment terms, fees, schedules, penalties, and financial obligations. Cite pages.",
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
      prompt:
        "Summarize employment terms: duties, compensation, leave, notice, and post-employment restrictions. Cite pages.",
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

export function personaActions(role?: string | null) {
  return DASHBOARD_ACTIONS[role || "individual"] || DASHBOARD_ACTIONS.individual;
}
