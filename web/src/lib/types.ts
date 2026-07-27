export type User = {
  id?: string;
  email: string;
  full_name?: string | null;
  role?: string;
  role_label?: string;
  welcome_message?: string;
  email_verified?: boolean;
  plan?: string;
  created_at?: string;
  document_count?: number;
};

export type DocumentRow = {
  id: string;
  original_filename: string;
  filename?: string;
  status: string;
  num_chunks?: number;
  processing_error?: string | null;
  file_size_bytes?: number;
  page_count?: number;
  has_tables?: boolean;
  created_at?: string;
};

export type Citation = {
  filename?: string;
  page?: number | null;
  snippet?: string | null;
};

export type ChatMessage = {
  id?: string;
  role: "user" | "assistant" | string;
  content: string;
  created_at?: string;
  sources?: Citation[];
  question_type?: string | null;
};

export type RecentConversation = {
  documentId: string;
  filename: string;
  preview: string;
  at: string;
  messageCount: number;
};

export type WorkspaceNotification = {
  id: string;
  kind: "processing" | "ready" | "failed" | "verify" | "info";
  title: string;
  body: string;
  href?: string;
  at?: string;
};

export type Confidence = {
  confidence_level?: string;
  confidence_score?: number | null;
  recommendation?: string | null;
  confidence_factors?: Record<string, number> | null;
};

export type DashboardAction = {
  id: string;
  kicker: string;
  title: string;
  desc: string;
  go: string;
  prompt?: string;
};

export type ExplainSection = {
  title: string;
  content: string;
  citations?: Citation[];
  missing?: boolean;
};

export type RiskItem = {
  title: string;
  severity?: string | null;
  explanation?: string;
  evidence_found?: boolean;
  citations?: Citation[];
};

export type ConsultSection = {
  title: string;
  content: string;
  citations?: Citation[];
  missing?: boolean;
};

export type Professional = {
  id: string;
  name: string;
  specialization: string;
  city?: string;
  distance_km?: number | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  verified?: boolean;
};
