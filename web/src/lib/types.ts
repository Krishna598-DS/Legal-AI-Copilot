export type User = {
  email: string;
  full_name?: string | null;
  role?: string;
  role_label?: string;
  welcome_message?: string;
};

export type DocumentRow = {
  id: string;
  original_filename: string;
  filename?: string;
  status: string;
  num_chunks?: number;
  processing_error?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant" | string;
  content: string;
};

export type Citation = {
  filename?: string;
  page?: number | null;
};

export type Confidence = {
  confidence_level?: string;
  confidence_score?: number | null;
  recommendation?: string | null;
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
