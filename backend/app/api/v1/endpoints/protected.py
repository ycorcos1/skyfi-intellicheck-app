from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user

router = APIRouter(tags=["auth"])


@router.get("/protected")
async def read_protected_route(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Basic protected endpoint used for authentication validation.
    Note: get_current_user is already applied as a router-level dependency,
    but we include it here explicitly for clarity and to access the user context.
    """

    return {
        "message": "Access granted",
        "user": {
            "user_id": current_user.get("user_id"),
            "username": current_user.get("username"),
            "email": current_user.get("email"),
        },
    }

