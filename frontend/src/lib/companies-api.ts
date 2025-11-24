import { ApiError, apiRequest } from "@/lib/api";
import { config } from "@/lib/config";
import type { AnalysisStatusResponse, Company, CompanyAnalysis, CompanyDetail, CompanyStatus } from "@/types/company";

export interface CompanyListResponse {
  items: Company[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface CompanyListParams {
  page?: number;
  limit?: number;
  search?: string;
  status?: CompanyStatus | "all";
  risk_min?: number;
  risk_max?: number;
  include_deleted?: boolean;
}

export interface CreateCompanyRequest {
  name: string;
  domain: string;
  website_url?: string;
  email: string;
  phone?: string;
}

export interface CreateCompanyResponse {
  company: Company;
  correlation_id: string;
}

function buildQueryString(params: CompanyListParams): string {
  const searchParams = new URLSearchParams();

  if (params.page) {
    searchParams.set("page", params.page.toString());
  }

  if (params.limit) {
    searchParams.set("limit", params.limit.toString());
  }

  if (params.search?.trim()) {
    searchParams.set("search", params.search.trim());
  }

  if (params.status && params.status !== "all") {
    searchParams.set("status", params.status);
  }

  if (typeof params.risk_min === "number") {
    searchParams.set("risk_min", params.risk_min.toString());
  }

  if (typeof params.risk_max === "number") {
    searchParams.set("risk_max", params.risk_max.toString());
  }

  if (params.include_deleted) {
    searchParams.set("include_deleted", "true");
  }

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export async function fetchCompanies(params: CompanyListParams, token: string | null) {
  const query = buildQueryString(params);
  return apiRequest<CompanyListResponse>(`/v1/companies${query}`, {
    token,
  });
}

export async function createCompany(payload: CreateCompanyRequest, token: string | null) {
  return apiRequest<CreateCompanyResponse>("/v1/companies", {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export async function fetchCompanyDetail(id: string, token: string | null) {
  return apiRequest<CompanyDetail>(`/v1/companies/${id}`, {
    token,
  });
}

export async function fetchCompanyAnalyses(id: string, token: string | null) {
  return apiRequest<CompanyAnalysis[]>(`/v1/companies/${id}/analyses`, {
    token,
  });
}

export async function fetchAnalysisStatus(id: string, token: string | null) {
  return apiRequest<AnalysisStatusResponse>(`/v1/companies/${id}/analysis/status`, {
    token,
  });
}

export async function reanalyzeCompany(id: string, retryFailedOnly: boolean, token: string | null) {
  return apiRequest<void>(`/v1/companies/${id}/reanalyze`, {
    method: "POST",
    body: JSON.stringify({ retry_failed_only: retryFailedOnly }),
    token,
  });
}

export async function revokeCompanyApproval(id: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${id}/revoke-approval`, {
    method: "POST",
    token,
  });
}

export async function markCompanyReviewComplete(id: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ action: "mark_review_complete" }),
    token,
  });
}

export async function markCompanySuspicious(id: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ action: "mark_suspicious" }),
    token,
  });
}

export async function autoApproveIfEligible(id: string, token: string | null) {
  return apiRequest<{ company_id: string; status: CompanyStatus; updated_at: string }>(
    `/v1/companies/${id}/auto-approve-if-eligible`,
    {
      method: "POST",
      token,
    }
  );
}

export async function exportCompanyJson(id: string, token: string | null, version?: number) {
  const query = typeof version === "number" ? `?version=${version}` : "";
  return fetchBinary(`/v1/companies/${id}/export/json${query}`, token);
}

async function fetchBinary(endpoint: string, token: string | null) {
  const url = `${config.api.baseUrl}${endpoint}`;
  const headers = new Headers();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    const response = await fetch(url, {
      method: "GET",
      headers,
    });

    if (response.status === 401) {
      // Don't do hard redirect here - let ProtectedLayout handle it
      // Hard redirects cause page reloads and can create loops
      throw new ApiError(401, "Unauthorized");
    }

    if (!response.ok) {
      let message = "Failed to generate export. Please try again.";
      let detail: unknown;

      try {
        detail = await response.json();
      } catch {
        detail = null;
      }

      if (detail && typeof (detail as { detail?: unknown }).detail === "string") {
        message = (detail as { detail?: string }).detail ?? message;
      } else if (response.status === 404) {
        message = "Analysis not found. Please refresh and try again.";
      } else if (response.status >= 500) {
        message = "Server error while generating export. Please try again later.";
      } else if (response.status === 400) {
        message = "Invalid export request. Please refresh and try again.";
      }

      throw new ApiError(response.status, message);
    }

    return response.blob();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(0, "Network error. Please check your connection.");
  }
}

export async function exportCompanyPdf(id: string, token: string | null, version?: number) {
  const query = typeof version === "number" ? `?version=${version}` : "";
  return fetchBinary(`/v1/companies/${id}/export/pdf${query}`, token);
}

export async function deleteCompany(id: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${id}`, {
    method: "DELETE",
    token,
  });
}

export interface BulkUploadResponse {
  created: Array<{ id: string; name: string; domain: string }>;
  errors: Array<{ index: number; error: string }>;
  total_processed: number;
  success_count: number;
  error_count: number;
}

export async function bulkUploadCompanies(file: File, token: string | null): Promise<BulkUploadResponse> {
  // Read file as JSON and send as JSON body
  const fileText = await file.text();
  const jsonData = JSON.parse(fileText);
  
  return apiRequest<BulkUploadResponse>("/v1/companies/bulk-upload", {
    method: "POST",
    body: JSON.stringify(jsonData),
    token,
  });
}

