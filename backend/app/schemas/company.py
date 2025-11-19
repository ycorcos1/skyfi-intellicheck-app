"""
Pydantic schemas for Company API request/response models.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.company import AnalysisStatus, CompanyStatus


class CompanyCreate(BaseModel):
    """Schema for creating a new company."""

    name: str = Field(..., min_length=1, max_length=255)
    domain: str = Field(..., min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)


class CompanyUpdate(BaseModel):
    """Schema for updating a company (only before first analysis)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    website_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)


class CompanyBase(BaseModel):
    """Base company schema shared across responses."""

    id: UUID
    name: str
    domain: str
    website_url: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    status: CompanyStatus
    risk_score: int
    analysis_status: AnalysisStatus
    current_step: Optional[str]
    last_analyzed_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyListItem(CompanyBase):
    """Company schema used in list responses."""

    pass


class CompanyAnalysisSummary(BaseModel):
    """Latest analysis summary returned with company detail."""

    id: UUID
    company_id: UUID
    version: int
    algorithm_version: str
    submitted_data: dict
    discovered_data: dict
    signals: List[dict]
    risk_score: int
    llm_summary: Optional[str]
    llm_details: Optional[str]
    is_complete: bool
    failed_checks: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyDetail(CompanyBase):
    """Detailed company response including latest analysis."""

    latest_analysis: Optional[CompanyAnalysisSummary] = None


class CompanyListResponse(BaseModel):
    """Paginated response for companies list."""

    items: List[CompanyListItem]
    total: int
    page: int
    limit: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class CompanyCreateResponse(BaseModel):
    """Response returned after creating a company."""

    company: CompanyBase
    correlation_id: str
    message: str = "Company created and analysis enqueued"


class ReanalyzeRequest(BaseModel):
    """Request body for triggering company reanalysis."""

    retry_failed_only: bool = False


class ReanalyzeResponse(BaseModel):
    """Response returned after enqueuing a reanalysis job."""

    company_id: UUID
    message: str
    retry_mode: Literal["full", "failed_only"]
    queued_at: datetime


class StatusUpdateRequest(BaseModel):
    """Request body for updating company status."""

    action: Literal[
        "mark_review_complete",
        "approve",
        "reject",
        "flag_fraudulent",
        "revoke_approval",
    ]


class StatusUpdateResponse(BaseModel):
    """Response returned after updating a company's status."""

    company_id: UUID
    status: CompanyStatus
    updated_at: datetime


class AnalysisStatusResponse(BaseModel):
    """Response payload for real-time analysis status polling."""

    company_id: UUID
    analysis_status: AnalysisStatus
    progress_percentage: int
    current_step: Optional[str]
    failed_checks: List[str] = Field(default_factory=list)
    last_updated: datetime


class ExportJSONResponse(BaseModel):
    """Schema for JSON export responses."""

    company: Dict[str, Any]
    analysis: Optional[Dict[str, Any]]



