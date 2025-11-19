"""
Wrapper module exposing application settings within the `app.core` namespace.

The canonical settings implementation lives in `backend/config.py`, and this module
re-exports the same helpers so that internal modules can consistently use
`from app.core.config import get_settings`.
"""

from config import Settings, get_settings

__all__ = ("Settings", "get_settings")



