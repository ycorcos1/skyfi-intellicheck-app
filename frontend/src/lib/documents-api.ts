import { ApiError, apiRequest } from "@/lib/api";
import type {
  Document,
  DocumentDownloadUrlResponse,
  DocumentListResponse,
  DocumentMetadataCreate,
  DocumentUploadUrlRequest,
  DocumentUploadUrlResponse,
} from "@/types/document";

export async function generateDocumentUploadUrl(
  companyId: string,
  payload: DocumentUploadUrlRequest,
  token: string | null,
) {
  return apiRequest<DocumentUploadUrlResponse>(`/v1/companies/${companyId}/documents/upload-url`, {
    method: "POST",
    body: JSON.stringify(payload),
    token,
  });
}

export async function persistDocumentMetadata(
  companyId: string,
  metadata: DocumentMetadataCreate,
  token: string | null,
) {
  return apiRequest<Document>(`/v1/companies/${companyId}/documents`, {
    method: "POST",
    body: JSON.stringify(metadata),
    token,
  });
}

export async function listDocuments(companyId: string, token: string | null) {
  return apiRequest<DocumentListResponse>(`/v1/companies/${companyId}/documents`, {
    token,
  });
}

export async function generateDocumentDownloadUrl(
  companyId: string,
  documentId: string,
  token: string | null,
) {
  return apiRequest<DocumentDownloadUrlResponse>(
    `/v1/companies/${companyId}/documents/${documentId}/download-url`,
    {
      token,
    },
  );
}

export async function deleteDocument(companyId: string, documentId: string, token: string | null) {
  return apiRequest<void>(`/v1/companies/${companyId}/documents/${documentId}`, {
    method: "DELETE",
    token,
  });
}

export async function uploadDocumentToS3(uploadUrl: string, file: File, signal?: AbortSignal) {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: {
      "Content-Type": file.type || "application/octet-stream",
    },
    signal,
  });

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to upload document.");
  }
}

