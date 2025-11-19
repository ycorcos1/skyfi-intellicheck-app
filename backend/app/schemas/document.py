"""
Pydantic schemas for document upload, metadata persistence, and retrieval.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadUrlRequest(BaseModel):
    """Request payload for generating a presigned upload URL."""

    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)  # Max 100 MB


class DocumentUploadUrlResponse(BaseModel):
    """Response payload containing presigned upload URL details."""

    document_id: UUID
    upload_url: str
    s3_key: str
    expires_in: int


class DocumentMetadataCreate(BaseModel):
    """Request payload for persisting document metadata after upload."""

    document_id: UUID
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0, le=100 * 1024 * 1024)
    mime_type: str = Field(..., min_length=1, max_length=100)
    document_type: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class DocumentResponse(BaseModel):
    """Representation of a single document record."""

    id: UUID
    company_id: UUID
    filename: str
    s3_key: str
    file_size: int
    mime_type: str
    uploaded_by: str
    document_type: Optional[str]
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """List response containing documents for a company."""

    items: List[DocumentResponse]
    total: int


class DocumentDownloadUrlResponse(BaseModel):
    """Response payload containing presigned download URL details."""

    download_url: str
    filename: str
    expires_in: int

