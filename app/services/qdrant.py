"""
Qdrant client service.

Builds QdrantClient from settings. Nginx Basic auth credentials are fetched
from AWS Secret Manager (finovaVectorDBPassword). Falls back to QDRANT_API_KEY
when password is empty but username is set.
"""

from __future__ import annotations

import base64
import os
from threading import Lock
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from qdrant_client import QdrantClient

from app.core.secret_manager import get_secret_manager
from app.utils.logger import get_logger

logger = get_logger("qdrant")

_lock = Lock()
_client: Optional[QdrantClient] = None
_client_key: Optional[Tuple[str, Optional[str]]] = None

QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "30"))
QDRANT_SEND_API_KEY = os.getenv("QDRANT_SEND_API_KEY", "true").lower() in ("1", "true", "yes")


def _get_qdrant_settings():
    from app.core.config import get_settings
    return get_settings(os.getenv("ENV", "dev"))


def _get_basic_password() -> str:
    """Fetch Qdrant basic auth password from secret manager."""
    try:
        sm = get_secret_manager()
        return sm.get_secret_value("finovaVectorDBPassword")
    except Exception:
        return ""


def _basic_authorization_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _build_client_kwargs(url: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Build kwargs for QdrantClient."""
    settings = _get_qdrant_settings()
    url = url.strip().rstrip("/")

    kwargs: Dict[str, Any] = {
        "url": url,
        "timeout": QDRANT_TIMEOUT,
        "check_compatibility": False,
    }

    if settings.qdrant_port:
        kwargs["port"] = settings.qdrant_port

    # Basic auth
    username = settings.qdrant_basic_user
    password = _get_basic_password()

    headers: Dict[str, str] = {}
    if username and password:
        headers["Authorization"] = _basic_authorization_header(username, password)
    if headers:
        kwargs["headers"] = headers

    # API key (sent separately to Qdrant if configured)
    if api_key and QDRANT_SEND_API_KEY:
        kwargs["api_key"] = api_key

    return kwargs


def get_qdrant_client(url: Optional[str] = None, api_key: Optional[str] = None) -> QdrantClient:
    """Thread-safe cached Qdrant client. Recreated when url/api_key changes."""
    global _client, _client_key

    settings = _get_qdrant_settings()
    resolved = (url or settings.qdrant_url).strip().rstrip("/")
    new_key = (resolved, api_key)

    with _lock:
        if _client is None or _client_key != new_key:
            if _client is not None:
                try:
                    _client.close()
                except Exception:
                    pass
            _client = QdrantClient(**_build_client_kwargs(resolved, api_key))
            _client_key = new_key
            logger.info("Qdrant client connected")
        return _client


def reset_qdrant_client() -> None:
    """Close and reset the cached client."""
    global _client, _client_key
    with _lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
        _client_key = None
