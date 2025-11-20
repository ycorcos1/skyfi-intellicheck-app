"""
Company CRUD endpoints with automatic analysis enqueueing and soft delete support.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.logging import get_logger, get_correlation_id
from app.core.metrics import get_metrics_client
from app.models.analysis import CompanyAnalysis
from app.models.company import AnalysisStatus, Company, CompanyStatus
from app.models.document import Document
from app.schemas.company import (
    CompanyCreate,
    CompanyCreateResponse,
    CompanyDetail,
    CompanyBase,
    CompanyListItem,
    CompanyListResponse,
    CompanyUpdate,
    CompanyAnalysisSummary,
    ReanalyzeRequest,
    ReanalyzeResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
    AnalysisStatusResponse,
    ExportJSONResponse,
)
from app.services.sqs_service import get_sqs_service
from app.services import export_service

logger = get_logger(__name__)

router = APIRouter(prefix="/companies", tags=["companies"])


STATUS_TRANSITIONS: Dict[tuple[CompanyStatus, str], CompanyStatus] = {
    (CompanyStatus.PENDING, "mark_review_complete"): CompanyStatus.APPROVED,
    (CompanyStatus.PENDING, "approve"): CompanyStatus.APPROVED,
    (CompanyStatus.PENDING, "reject"): CompanyStatus.REJECTED,
    (CompanyStatus.PENDING, "flag_fraudulent"): CompanyStatus.FRAUDULENT,
    (CompanyStatus.APPROVED, "flag_fraudulent"): CompanyStatus.FRAUDULENT,
    (CompanyStatus.APPROVED, "revoke_approval"): CompanyStatus.REVOKED,
}


def _apply_status_action(company: Company, action: str) -> CompanyStatus:
    """Validate and apply a status transition."""
    transition_key = (company.status, action)
    new_status = STATUS_TRANSITIONS.get(transition_key)
    if new_status is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {company.status.value} -> {action}",
        )
    company.status = new_status
    return new_status


def _calculate_progress_percentage(
    analysis_status: AnalysisStatus, current_step: Optional[str]
) -> int:
    """Calculate analysis progress percentage based on current step."""
    if analysis_status in {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED, AnalysisStatus.INCOMPLETE}:
        return 100

    step_order = ["whois", "dns", "mx_validation", "website_scrape", "llm_processing"]
    step_aliases = {"phone": "website_scrape", "complete": "llm_processing"}
    normalized_step = step_aliases.get(current_step or "", current_step)

    if not normalized_step or normalized_step not in step_order:
        return 0

    step_index = step_order.index(normalized_step)
    total_steps = len(step_order)

    # step_index represents completed steps count because worker advances to next step after completion
    progress = int((step_index / total_steps) * 100)
    # Clamp between 0 and 99 to avoid 100 before completion
    return max(0, min(progress, 99))


def _perform_status_update(
    db: Session,
    company_id: UUID,
    action: str,
    current_user: Optional[Dict[str, Any]] = None,
) -> StatusUpdateResponse:
    """Execute a status transition and persist changes."""
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    try:
        new_status = _apply_status_action(company, action)
        company.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(company)

        correlation_id = get_correlation_id() or "unknown"
        logger.info(
            "Company status updated",
            extra={
                "company_id": str(company_id),
                "old_status": company.status.value if hasattr(company, 'status') else None,
                "new_status": new_status.value,
                "action": action,
                "user_id": (current_user or {}).get("user_id"),
                "correlation_id": correlation_id,
            }
        )

        return StatusUpdateResponse(
            company_id=company.id,
            status=company.status,
            updated_at=company.updated_at,
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to update company status",
            extra={
                "company_id": str(company_id),
                "action": action,
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company status. Please try again later.",
        ) from exc


@router.post(
    "",
    response_model=CompanyCreateResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new company and enqueue analysis",
)
async def create_company(
    company_data: CompanyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Create a company record and immediately enqueue an analysis job via SQS.

    Business rules:
    - New companies start with status=pending, analysis_status=pending, risk_score=0.
    - A correlation ID is returned for tracking the SQS message.
    """
    correlation_id = get_correlation_id() or "unknown"
    try:
        # Normalize inputs
        name = company_data.name.strip()
        domain = company_data.domain.strip().lower()
        website_url = company_data.website_url.strip() if company_data.website_url else None

        company = Company(
            name=name,
            domain=domain,
            website_url=website_url,
            email=company_data.email,
            phone=company_data.phone,
            status=CompanyStatus.PENDING,
            analysis_status=AnalysisStatus.PENDING,
            risk_score=0,
        )

        db.add(company)
        db.flush()  # Obtain primary key before external calls

        sqs_service = get_sqs_service()
        sqs_response = sqs_service.enqueue_analysis(
            company_id=str(company.id),
            retry_mode="full",
            correlation_id=correlation_id,
        )
        message_id = sqs_response.get("MessageId", "unknown")

        db.commit()
        db.refresh(company)

        logger.info(
            "Created company and enqueued analysis",
            extra={
                "company_id": str(company.id),
                "company_name": company.name,
                "domain": company.domain,
                "user_id": current_user.get("user_id"),
                "correlation_id": correlation_id,
                "sqs_message_id": message_id,
            }
        )

        # Record metric for company creation
        metrics = get_metrics_client()
        metrics.put_metric(
            "CompanyCreated",
            1,
            "Count",
            dimensions={"Status": "pending"}
        )

        return CompanyCreateResponse(
            company=CompanyBase.model_validate(company),
            correlation_id=correlation_id,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to create company",
            extra={
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create company. Please try again later.",
        ) from exc


@router.get(
    "",
    response_model=CompanyListResponse,
    summary="List companies with filtering and pagination",
)
async def list_companies(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Case-insensitive search by company name"),
    status: Optional[CompanyStatus] = Query(None, description="Filter by company status"),
    risk_min: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score"),
    risk_max: Optional[int] = Query(None, ge=0, le=100, description="Maximum risk score"),
    include_deleted: bool = Query(False, description="Include soft-deleted companies"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Retrieve a paginated list of companies with optional filtering capabilities.
    """
    try:
        logger.info("Listing companies", extra={"page": page, "limit": limit, "user_id": current_user.get("user_id")})
        
        if risk_min is not None and risk_max is not None and risk_min > risk_max:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="risk_min cannot be greater than risk_max",
            )

        # Build query step by step with error handling
        try:
            query = db.query(Company)
            
            if not include_deleted:
                query = query.filter(Company.is_deleted == False)

            if search:
                query = query.filter(Company.name.ilike(f"%{search.strip()}%"))

            if status:
                query = query.filter(Company.status == status)

            if risk_min is not None:
                query = query.filter(Company.risk_score >= risk_min)
            if risk_max is not None:
                query = query.filter(Company.risk_score <= risk_max)

            # Get total count
            total = query.count()
            pages = (total + limit - 1) // limit if total else 0

            # Get items
            items = (
                query.order_by(Company.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            
            logger.debug(f"Found {len(items)} companies, total: {total}")
            
        except Exception as db_exc:
            logger.error("Database query error: %s", str(db_exc), exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database query failed",
            ) from db_exc

        # Convert to response models with error handling
        try:
            company_items = []
            for item in items:
                try:
                    company_items.append(CompanyListItem.model_validate(item))
                except Exception as validation_exc:
                    logger.error("Model validation error for company %s: %s", item.id, str(validation_exc))
                    # Skip invalid items rather than failing entire request
                    continue
            
            return CompanyListResponse(
                items=company_items,
                total=total,
                page=page,
                limit=limit,
                pages=max(pages, 1) if total else 0,
            )
        except Exception as validation_exc:
            logger.error("Response model validation error: %s", str(validation_exc), exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to format response",
            ) from validation_exc
            
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error listing companies: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve companies. Please try again later.",
        ) from exc


@router.get(
    "/{company_id}",
    response_model=CompanyDetail,
    summary="Retrieve a single company with latest analysis",
)
async def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Return company details along with the latest analysis record, if available.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    latest_analysis = (
        db.query(CompanyAnalysis)
        .filter(CompanyAnalysis.company_id == company_id)
        .order_by(CompanyAnalysis.version.desc())
        .first()
    )

    company_detail = CompanyDetail.model_validate(company)
    if latest_analysis:
        company_detail.latest_analysis = CompanyAnalysisSummary.model_validate(latest_analysis)

    return company_detail


@router.patch(
    "/{company_id}",
    response_model=CompanyBase,
    summary="Update company details (before first analysis only)",
)
async def update_company(
    company_id: UUID,
    company_update: CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update mutable fields for a company.

    Business rule: companies become immutable once `last_analyzed_at` is set.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    if company.last_analyzed_at is not None:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Company cannot be edited after analysis. Please request re-analysis instead.",
        )

    update_data = company_update.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "domain" in update_data and update_data["domain"]:
        update_data["domain"] = update_data["domain"].strip().lower()
    if "website_url" in update_data and update_data["website_url"]:
        update_data["website_url"] = update_data["website_url"].strip()

    for field, value in update_data.items():
        setattr(company, field, value)

    try:
        db.commit()
        db.refresh(company)
        correlation_id = get_correlation_id() or "unknown"
        logger.info(
            "Updated company",
            extra={
                "company_id": str(company_id),
                "user_id": current_user.get("user_id"),
                "correlation_id": correlation_id,
            }
        )
        return CompanyBase.model_validate(company)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to update company",
            extra={
                "company_id": str(company_id),
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update company. Please try again later.",
        ) from exc


@router.delete(
    "/{company_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Permanently delete a company",
)
async def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Permanently delete a company and all associated data from the database.
    Also deletes all associated S3 documents.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    correlation_id = get_correlation_id() or "unknown"
    
    try:
        # Delete all S3 documents associated with this company
        from app.services.s3_service import get_s3_service
        s3_service = get_s3_service()
        
        # Get all documents for this company before deletion
        documents = db.query(Document).filter(Document.company_id == company_id).all()
        
        deleted_s3_count = 0
        failed_s3_count = 0
        
        for document in documents:
            try:
                if s3_service.delete_object(document.s3_key):
                    deleted_s3_count += 1
                else:
                    failed_s3_count += 1
                    logger.warning(
                        "Failed to delete S3 object for document",
                        extra={
                            "company_id": str(company_id),
                            "document_id": str(document.id),
                            "s3_key": document.s3_key,
                            "correlation_id": correlation_id,
                        }
                    )
            except Exception as s3_error:
                failed_s3_count += 1
                logger.error(
                    "Error deleting S3 object for document",
                    extra={
                        "company_id": str(company_id),
                        "document_id": str(document.id),
                        "s3_key": document.s3_key,
                        "error": str(s3_error),
                        "correlation_id": correlation_id,
                    },
                    exc_info=True
                )
        
        # Permanently delete the company from database
        # CASCADE will automatically delete: analyses, documents, notes
        db.delete(company)
        db.commit()
        
        logger.info(
            "Permanently deleted company",
            extra={
                "company_id": str(company_id),
                "company_name": company.name,
                "user_id": current_user.get("user_id"),
                "correlation_id": correlation_id,
                "s3_documents_deleted": deleted_s3_count,
                "s3_documents_failed": failed_s3_count,
            }
        )
        
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to delete company",
            extra={
                "company_id": str(company_id),
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete company. Please try again later.",
        ) from exc


@router.post(
    "/{company_id}/restore",
    response_model=CompanyBase,
    summary="Restore a soft-deleted company",
)
async def restore_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Restore a previously soft-deleted company.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    if not company.is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Company is not deleted",
        )

    company.is_deleted = False

    try:
        db.commit()
        db.refresh(company)
        correlation_id = get_correlation_id() or "unknown"
        logger.info(
            "Restored company",
            extra={
                "company_id": str(company_id),
                "user_id": current_user.get("user_id"),
                "correlation_id": correlation_id,
            }
        )
        return CompanyBase.model_validate(company)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to restore company",
            extra={
                "company_id": str(company_id),
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore company. Please try again later.",
        ) from exc


@router.post(
    "/{company_id}/reanalyze",
    response_model=ReanalyzeResponse,
    summary="Trigger company reanalysis (full or failed-only)",
)
async def reanalyze_company(
    company_id: UUID,
    request: ReanalyzeRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Re-enqueue an analysis job for a company."""
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    retry_mode = "failed_only" if request.retry_failed_only else "full"
    failed_checks: list[str] = []

    if retry_mode == "failed_only":
        latest_analysis = (
            db.query(CompanyAnalysis)
            .filter(CompanyAnalysis.company_id == company_id)
            .order_by(CompanyAnalysis.created_at.desc())
            .first()
        )
        if latest_analysis is None:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="No previous analysis found to retry failed checks.",
            )
        failed_checks = latest_analysis.failed_checks or []
        if not failed_checks:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Latest analysis has no failed checks to retry.",
            )

    queued_at = datetime.utcnow()

    try:
        company.analysis_status = AnalysisStatus.PENDING
        company.current_step = None
        company.updated_at = queued_at

        sqs_service = get_sqs_service()
        sqs_response = sqs_service.enqueue_analysis(
            company_id=str(company.id),
            retry_mode=retry_mode,
            failed_checks=failed_checks or None,
        )

        db.commit()
        db.refresh(company)

        correlation_id = get_correlation_id() or "unknown"
        message_id = sqs_response.get("MessageId", "unknown")

        logger.info(
            "Reanalysis enqueued",
            extra={
                "company_id": str(company_id),
                "retry_mode": retry_mode,
                "failed_checks": failed_checks,
                "correlation_id": correlation_id,
                "sqs_message_id": message_id,
                "user_id": current_user.get("user_id"),
            }
        )

        # Record metric for reanalysis
        metrics = get_metrics_client()
        metrics.put_metric(
            "ReanalysisEnqueued",
            1,
            "Count",
            dimensions={"RetryMode": retry_mode}
        )

        return ReanalyzeResponse(
            company_id=company.id,
            message="Analysis queued",
            retry_mode=retry_mode,
            queued_at=queued_at,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to enqueue reanalysis",
            extra={
                "company_id": str(company_id),
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue analysis. Please try again later.",
        ) from exc


@router.patch(
    "/{company_id}/status",
    response_model=StatusUpdateResponse,
    summary="Update company status via state machine action",
)
async def update_company_status(
    company_id: UUID,
    request: StatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Update a company status according to business rules."""
    return _perform_status_update(
        db=db,
        company_id=company_id,
        action=request.action,
        current_user=current_user,
    )


@router.post(
    "/{company_id}/flag-fraudulent",
    response_model=StatusUpdateResponse,
    summary="Flag a company as fraudulent",
)
async def flag_company_fraudulent(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Flag a company as fraudulent."""
    return _perform_status_update(
        db=db,
        company_id=company_id,
        action="flag_fraudulent",
        current_user=current_user,
    )


@router.post(
    "/{company_id}/revoke-approval",
    response_model=StatusUpdateResponse,
    summary="Revoke company approval",
)
async def revoke_company_approval(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Revoke an approved company."""
    return _perform_status_update(
        db=db,
        company_id=company_id,
        action="revoke_approval",
        current_user=current_user,
    )


@router.post(
    "/{company_id}/auto-approve-if-eligible",
    response_model=StatusUpdateResponse,
    summary="Auto-approve company if eligible (analysis=COMPLETED, risk_score<=30, status=PENDING)",
)
async def auto_approve_if_eligible(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Auto-approve a company if it meets eligibility criteria.
    
    Eligibility:
    - analysis_status must be COMPLETED
    - risk_score must be <= 30
    - status must be PENDING
    
    This is useful for migrating existing companies that were analyzed before
    the auto-approve logic was implemented in the Lambda worker.
    """
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )
    
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )
    
    # Check eligibility
    if company.analysis_status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Company analysis is not completed (current: {company.analysis_status.value})",
        )
    
    if company.risk_score > 30:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Company risk score ({company.risk_score}) exceeds threshold (30)",
        )
    
    if company.status != CompanyStatus.PENDING:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Company status is not PENDING (current: {company.status.value})",
        )
    
    # Auto-approve
    try:
        company.status = CompanyStatus.APPROVED
        company.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(company)
        
        correlation_id = get_correlation_id() or "unknown"
        logger.info(
            "Company auto-approved",
            extra={
                "company_id": str(company_id),
                "risk_score": company.risk_score,
                "analysis_status": company.analysis_status.value,
                "user_id": (current_user or {}).get("user_id"),
                "correlation_id": correlation_id,
            }
        )
        
        return StatusUpdateResponse(
            company_id=company.id,
            status=company.status,
            updated_at=company.updated_at,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to auto-approve company",
            extra={
                "company_id": str(company_id),
                "error": str(exc),
                "correlation_id": correlation_id,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to auto-approve company. Please try again later.",
        ) from exc


@router.get(
    "/{company_id}/analysis/status",
    response_model=AnalysisStatusResponse,
    summary="Retrieve real-time analysis status for a company",
)
async def get_analysis_status(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Return the current analysis status, progress, and failed checks."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None or company.is_deleted:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    progress = _calculate_progress_percentage(company.analysis_status, company.current_step)
    if company.analysis_status in {
        AnalysisStatus.COMPLETED,
        AnalysisStatus.FAILED,
        AnalysisStatus.INCOMPLETE,
    }:
        progress = 100

    failed_checks: list[str] = []
    if company.analysis_status in {AnalysisStatus.FAILED, AnalysisStatus.INCOMPLETE}:
        latest_analysis = (
            db.query(CompanyAnalysis)
            .filter(CompanyAnalysis.company_id == company_id)
            .order_by(CompanyAnalysis.created_at.desc())
            .first()
        )
        if latest_analysis and latest_analysis.failed_checks:
            failed_checks = latest_analysis.failed_checks

    correlation_id = get_correlation_id() or "unknown"
    logger.debug(
        "Retrieved analysis status",
        extra={
            "company_id": str(company_id),
            "analysis_status": company.analysis_status.value,
            "current_step": company.current_step,
            "progress_percentage": progress,
            "correlation_id": correlation_id,
        }
    )

    return AnalysisStatusResponse(
        company_id=company.id,
        analysis_status=company.analysis_status,
        progress_percentage=progress,
        current_step=company.current_step,
        failed_checks=failed_checks,
        last_updated=company.updated_at,
    )


@router.get(
    "/{company_id}/analyses",
    response_model=List[CompanyAnalysisSummary],
    summary="Retrieve all analysis versions for a company",
)
async def list_company_analyses(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[CompanyAnalysisSummary]:
    """Return all analysis versions for a company ordered by version descending."""

    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )

    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    analyses = (
        db.query(CompanyAnalysis)
        .filter(CompanyAnalysis.company_id == company_id)
        .order_by(CompanyAnalysis.version.desc())
        .all()
    )

    correlation_id = get_correlation_id() or "unknown"
    logger.debug(
        "Retrieved company analysis history",
        extra={
            "company_id": str(company_id),
            "analysis_count": len(analyses),
            "user_id": current_user.get("user_id"),
            "correlation_id": correlation_id,
        },
    )

    return [CompanyAnalysisSummary.model_validate(analysis) for analysis in analyses]


@router.get(
    "/{company_id}/export/json",
    response_model=ExportJSONResponse,
    summary="Export company verification report as JSON",
)
async def export_company_json(
    company_id: UUID,
    version: Optional[int] = Query(
        default=None,
        ge=1,
        description="Specific analysis version to export. Defaults to the latest version.",
    ),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Generate a structured JSON export for a company and a specific analysis version (latest by default).
    """
    company, analysis = export_service.fetch_company_with_analysis(db, company_id, version)
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    if version is not None and analysis is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Analysis version {version} not found for company {company_id}",
        )

    resolved_version = analysis.version if analysis else version

    report = export_service.generate_json_report(company, analysis)

    correlation_id = get_correlation_id() or "unknown"
    logger.info(
        "JSON export requested",
        extra={
            "company_id": str(company_id),
            "user_id": current_user.get("user_id"),
            "correlation_id": correlation_id,
            "analysis_version": resolved_version,
        },
    )
    
    # Record export metric
    metrics = get_metrics_client()
    metrics.put_metric("ExportRequested", 1, "Count", dimensions={"Format": "json"})

    return report


@router.get(
    "/{company_id}/export/pdf",
    summary="Export company verification report as PDF",
    responses={200: {"content": {"application/pdf": {}}}},
)
async def export_company_pdf(
    company_id: UUID,
    version: Optional[int] = Query(
        default=None,
        ge=1,
        description="Specific analysis version to export. Defaults to the latest version.",
    ),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Generate and stream a PDF export for the specified company and analysis version (latest by default).
    """
    company, analysis = export_service.fetch_company_with_analysis(db, company_id, version)
    if company is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )

    if version is not None and analysis is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Analysis version {version} not found for company {company_id}",
        )

    resolved_version = analysis.version if analysis else version

    try:
        pdf_bytes = export_service.generate_pdf_report(company, analysis)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        correlation_id = get_correlation_id() or "unknown"
        logger.error(
            "Failed to generate PDF export",
            extra={
                "company_id": str(company_id),
            "error": str(exc),
                "correlation_id": correlation_id,
                "analysis_version": resolved_version,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report. Please try again later.",
        ) from exc

    correlation_id = get_correlation_id() or "unknown"
    logger.info(
        "PDF export requested",
        extra={
            "company_id": str(company_id),
            "user_id": current_user.get("user_id"),
            "pdf_size_bytes": len(pdf_bytes),
            "correlation_id": correlation_id,
            "analysis_version": resolved_version,
        }
    )
    
    # Record export metric
    metrics = get_metrics_client()
    metrics.put_metric("ExportRequested", 1, "Count", dimensions={"Format": "pdf"})

    safe_name = "".join(
        c for c in company.name if c.isalnum() or c in (" ", "-", "_")
    ).strip()
    if not safe_name:
        safe_name = str(company.id)
    filename = f"company_{safe_name.replace(' ', '_')}_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


