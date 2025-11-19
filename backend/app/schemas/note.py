"""
Pydantic schemas for internal notes request/response payloads.
"""
from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    """Request payload for creating a new note."""

    content: str = Field(..., min_length=1, max_length=10_000)


class NoteUpdate(BaseModel):
    """Request payload for updating an existing note."""

    content: str = Field(..., min_length=1, max_length=10_000)


class NoteResponse(BaseModel):
    """Representation of a single note."""

    id: UUID
    company_id: UUID
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NoteListResponse(BaseModel):
    """List response containing notes for a company."""

    items: List[NoteResponse]
    total: int


