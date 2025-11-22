export type CompanyStatus = "pending" | "approved" | "rejected" | "fraudulent" | "revoked";

export type AnalysisStatus = "pending" | "in_progress" | "completed" | "failed" | "incomplete";

export type CurrentStep =
  | "whois"
  | "dns"
  | "mx_validation"
  | "website_scrape"
  | "llm_processing"
  | "complete";

export interface SubmittedData {
  name?: string;
  domain?: string;
  email?: string;
  phone?: string;
  website_url?: string;
  [key: string]: unknown;
}

export interface DiscoveredData {
  domain_age_months?: number;
  whois_privacy_enabled?: boolean;
  mx_records_valid?: boolean;
  website_reachable?: boolean;
  ssl_certificate_valid?: boolean;
  [key: string]: unknown;
}

export type SignalStatus = "ok" | "suspicious" | "mismatch" | "warning";

export interface AnalysisSignal {
  field: string;
  value: string;
  status: SignalStatus;
  weight?: number;
  description?: string;
}

export interface CompanyAnalysis {
  id: string;
  company_id: string;
  version: number;
  algorithm_version: string;
  submitted_data: SubmittedData;
  discovered_data: DiscoveredData;
  signals: AnalysisSignal[];
  risk_score: number;
  llm_summary: string | null;
  llm_details?: string | null;
  is_complete: boolean;
  failed_checks: string[];
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string;
  website_url: string;
  email: string;
  phone: string;
  status: CompanyStatus;
  risk_score: number;
  analysis_status: AnalysisStatus;
  current_step?: CurrentStep | null;
  last_analyzed_at: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  [key: string]: unknown;
}

export interface CompanyDetail extends Company {
  latest_analysis: CompanyAnalysis | null;
}

export interface AnalysisStatusResponse {
  status: AnalysisStatus;
  progress_percentage: number;
  current_step: CurrentStep | null;
}

