from fastapi import APIRouter, Depends

from app.api.v1.endpoints import companies, documents, notes, protected
from app.core.auth import get_current_user

# Main API router for versioned endpoints
api_router = APIRouter(prefix="/v1", dependencies=[Depends(get_current_user)])
api_router.include_router(protected.router)
api_router.include_router(companies.router)
api_router.include_router(documents.router)
api_router.include_router(notes.router)

