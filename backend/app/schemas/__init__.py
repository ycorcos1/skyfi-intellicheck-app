"""
Pydantic schemas for request/response models will live in this package.
"""

from app.schemas.company import (
    CompanyBase,
    CompanyCreate,
    CompanyCreateResponse,
    CompanyDetail,
    CompanyListItem,
    CompanyListResponse,
    CompanyUpdate,
)
from app.schemas.document import (
    DocumentDownloadUrlResponse,
    DocumentListResponse,
    DocumentMetadataCreate,
    DocumentResponse,
    DocumentUploadUrlRequest,
    DocumentUploadUrlResponse,
)
from app.schemas.note import (
    NoteCreate,
    NoteListResponse,
    NoteResponse,
    NoteUpdate,
)

__all__ = [
    "CompanyBase",
    "CompanyCreate",
    "CompanyCreateResponse",
    "CompanyDetail",
    "CompanyListItem",
    "CompanyListResponse",
    "CompanyUpdate",
    "DocumentDownloadUrlResponse",
    "DocumentListResponse",
    "DocumentMetadataCreate",
    "DocumentResponse",
    "DocumentUploadUrlRequest",
    "DocumentUploadUrlResponse",
    "NoteCreate",
    "NoteListResponse",
    "NoteResponse",
    "NoteUpdate",
]
