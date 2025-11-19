"""
Internal notes CRUD endpoints for operator collaboration.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.company import Company
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteListResponse, NoteResponse, NoteUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["notes"])


def _get_active_company_or_404(db: Session, company_id: UUID) -> Company:
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


def _get_note_or_404(
    db: Session,
    company_id: UUID,
    note_id: UUID,
) -> Note:
    note = (
        db.query(Note)
        .join(Company, Note.company_id == Company.id)
        .filter(
            Note.id == note_id,
            Note.company_id == company_id,
            Company.is_deleted.is_(False),
        )
        .first()
    )
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note {note_id} not found for company {company_id}",
        )
    return note


def _get_actor_id(current_user: Dict[str, Any]) -> str:
    return current_user.get("user_id") or current_user.get("email") or "unknown"


def _sanitize_content(content: str) -> str:
    sanitized = content.strip()
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Content cannot be empty or whitespace.",
        )
    return sanitized


@router.post(
    "/{company_id}/notes",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an internal note for a company",
)
async def create_note(
    company_id: UUID,
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> NoteResponse:
    """
    Create a new note attached to the specified company.
    """
    _get_active_company_or_404(db, company_id)

    content = _sanitize_content(note_data.content)
    actor_id = _get_actor_id(current_user)

    note = Note(
        company_id=company_id,
        user_id=actor_id,
        content=content,
    )

    try:
        db.add(note)
        db.commit()
        db.refresh(note)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to create note for company %s by user %s: %s",
            company_id,
            actor_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create note. Please try again later.",
        ) from exc

    logger.info(
        "Created note %s for company %s by user %s",
        note.id,
        company_id,
        actor_id,
    )

    return NoteResponse.model_validate(note)


@router.get(
    "/{company_id}/notes",
    response_model=NoteListResponse,
    summary="List notes for a company",
)
async def list_notes(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> NoteListResponse:
    """
    Retrieve all notes for the specified company ordered by newest first.
    """
    _get_active_company_or_404(db, company_id)

    notes = (
        db.query(Note)
        .filter(Note.company_id == company_id)
        .order_by(Note.created_at.desc())
        .all()
    )
    actor_id = _get_actor_id(current_user)

    logger.debug(
        "Retrieved %s notes for company %s by user %s",
        len(notes),
        company_id,
        actor_id,
    )

    return NoteListResponse(
        items=[NoteResponse.model_validate(note) for note in notes],
        total=len(notes),
    )


@router.patch(
    "/{company_id}/notes/{note_id}",
    response_model=NoteResponse,
    summary="Update an existing note",
)
async def update_note(
    company_id: UUID,
    note_id: UUID,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> NoteResponse:
    """
    Update the content of an existing note. Only the author may update their note.
    """
    note = _get_note_or_404(db, company_id, note_id)

    actor_id = _get_actor_id(current_user)

    if note.user_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit notes you created.",
        )

    content = _sanitize_content(note_update.content)

    note.content = content
    note.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(note)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to update note %s for company %s by user %s: %s",
            note_id,
            company_id,
            actor_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update note. Please try again later.",
        ) from exc

    logger.info(
        "Updated note %s for company %s by user %s",
        note_id,
        company_id,
        actor_id,
    )

    return NoteResponse.model_validate(note)


@router.delete(
    "/{company_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
)
async def delete_note(
    company_id: UUID,
    note_id: UUID,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    """
    Permanently delete a note. Only the author may delete their note.
    """
    note = _get_note_or_404(db, company_id, note_id)

    actor_id = _get_actor_id(current_user)

    if note.user_id != actor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete notes you created.",
        )

    try:
        db.delete(note)
        db.commit()
    except Exception as exc:  # pylint: disable=broad-exception-caught
        db.rollback()
        logger.error(
            "Failed to delete note %s for company %s by user %s: %s",
            note_id,
            company_id,
            actor_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete note. Please try again later.",
        ) from exc

    logger.info(
        "Deleted note %s for company %s by user %s",
        note_id,
        company_id,
        actor_id,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


