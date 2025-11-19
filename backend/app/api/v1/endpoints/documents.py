"""
Document management endpoints for uploading, listing, downloading, and deleting
company documents via S3 presigned URLs.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.company import Company
from app.models.document import Document
from app.schemas.document import (
    DocumentDownloadUrlResponse,
    DocumentListResponse,
    DocumentMetadataCreate,
    DocumentResponse,
    DocumentUploadUrlRequest,
    DocumentUploadUrlResponse,
)
from app.services.s3_service import S3Service, get_s3_service

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/companies", tags=["documents"])


def _get_company_or_404(db: Session, company_id: UUID) -> Company:
    company = (
        db.query(Company)
        .filter(Company.id == company_id, Company.is_deleted.is_(False))
        .first()
    )
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )
    return company


def _get_document_or_404(
    db: Session,
    company_id: UUID,
    document_id: UUID,
) -> Document:
    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.company_id == company_id,
        )
        .first()
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found for company {company_id}",
        )
    return document


@router.post(
    "/{company_id}/documents/upload-url",
    response_model=DocumentUploadUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate presigned URL for document upload",
)
async def generate_document_upload_url(
    company_id: UUID,
    payload: DocumentUploadUrlRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DocumentUploadUrlResponse:
    """
    Provide a presigned S3 PUT URL so the client can upload a document directly.
    """
    _get_company_or_404(db, company_id)

    document_id = uuid.uuid4()
    s3_service = get_s3_service()
    logger.info(
        "Generating upload URL for company %s by user %s (filename=%s, size=%s)",
        company_id,
        current_user.get("user_id"),
        payload.filename,
        payload.file_size,
    )

    upload_data = s3_service.generate_upload_url(
        company_id=company_id,
        document_id=document_id,
        filename=payload.filename,
        mime_type=payload.mime_type,
    )

    return DocumentUploadUrlResponse(
        document_id=document_id,
        upload_url=upload_data["upload_url"],
        s3_key=upload_data["s3_key"],
        expires_in=settings.s3_upload_expiration,
    )


@router.post(
    "/{company_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Persist document metadata after successful upload",
)
async def create_document_metadata(
    company_id: UUID,
    metadata: DocumentMetadataCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DocumentResponse:
    """
    Persist metadata for a document that has been uploaded to S3.
    """
    _get_company_or_404(db, company_id)

    existing = db.query(Document).filter(Document.id == metadata.document_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document {metadata.document_id} already exists",
        )

    s3_key = S3Service.generate_s3_key(
        company_id=company_id,
        document_id=metadata.document_id,
        filename=metadata.filename,
    )

    document = Document(
        id=metadata.document_id,
        company_id=company_id,
        filename=metadata.filename,
        s3_key=s3_key,
        file_size=metadata.file_size,
        mime_type=metadata.mime_type,
        uploaded_by=current_user.get("user_id") or current_user.get("email") or "unknown",
        document_type=metadata.document_type,
        description=metadata.description,
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to persist metadata for document %s: %s",
            metadata.document_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save document metadata. Please try again later.",
        ) from exc

    logger.info(
        "Persisted document metadata for company %s document %s by user %s",
        company_id,
        document.id,
        current_user.get("user_id"),
    )

    return DocumentResponse.model_validate(document)


@router.get(
    "/{company_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents for a company",
)
async def list_company_documents(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DocumentListResponse:
    """
    Retrieve all documents associated with a company, ordered by most recent.
    """
    _get_company_or_404(db, company_id)

    documents = (
        db.query(Document)
        .filter(Document.company_id == company_id)
        .order_by(Document.created_at.desc())
        .all()
    )

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(doc) for doc in documents],
        total=len(documents),
    )


@router.get(
    "/{company_id}/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
    summary="Generate presigned URL for downloading a document",
)
async def generate_document_download_url(
    company_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> DocumentDownloadUrlResponse:
    """
    Provide a presigned S3 GET URL for the requested document.
    """
    document = _get_document_or_404(db, company_id, document_id)
    s3_service = get_s3_service()

    download_url = s3_service.generate_download_url(
        s3_key=document.s3_key,
        filename=document.filename,
    )

    logger.info(
        "Generated download URL for company %s document %s",
        company_id,
        document_id,
    )

    return DocumentDownloadUrlResponse(
        download_url=download_url,
        filename=document.filename,
        expires_in=settings.s3_download_expiration,
    )


@router.delete(
    "/{company_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    company_id: UUID,
    document_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """
    Delete a document's metadata and remove the file from S3.
    """
    document = _get_document_or_404(db, company_id, document_id)
    s3_service = get_s3_service()

    s3_deleted = s3_service.delete_object(document.s3_key)
    if not s3_deleted:
        logger.warning(
            "S3 deletion failed for company %s document %s; metadata will still be removed",
            company_id,
            document_id,
        )

    try:
        db.delete(document)
        db.commit()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to delete document %s for company %s: %s",
            document_id,
            company_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document. Please try again later.",
        ) from exc

    logger.info(
        "Deleted document %s for company %s",
        document_id,
        company_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)

