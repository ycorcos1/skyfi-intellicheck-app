export interface Document {
  id: string;
  company_id: string;
  filename: string;
  s3_key: string;
  file_size: number;
  mime_type: string;
  uploaded_by: string;
  document_type?: string | null;
  description?: string | null;
  created_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}

export interface DocumentUploadUrlRequest {
  filename: string;
  file_size: number;
  mime_type: string;
}

export interface DocumentUploadUrlResponse {
  document_id: string;
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface DocumentMetadataCreate {
  document_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  document_type?: string | null;
  description?: string | null;
}

export interface DocumentDownloadUrlResponse {
  download_url: string;
  filename: string;
  expires_in: number;
}

