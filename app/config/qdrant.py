"""
Qdrant client service.

Builds QdrantClient with nginx Basic auth from env.py values
(fetched via Secret Manager or env fallbacks).
"""

from __future__ import annotations

import base64
import os
from threading import Lock
from typing import Any, Dict, Optional, Tuple

from qdrant_client import QdrantClient

from app.config.env import QDRANT_URL, QDRANT_API_KEY, QDRANT_BASIC_USER, QDRANT_BASIC_PASSWORD
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger("qdrant")

settings = get_settings()

_lock = Lock()
_client: Optional[QdrantClient] = None
_client_key: Optional[Tuple[str, Optional[str]]] = None

QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "30"))
QDRANT_SEND_API_KEY = os.getenv("QDRANT_SEND_API_KEY", "true").lower() in ("1", "true", "yes")


def _basic_authorization_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _build_client_kwargs(url: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Build kwargs for QdrantClient."""
    url = url.strip().rstrip("/")

    kwargs: Dict[str, Any] = {
        "url": url,
        "timeout": QDRANT_TIMEOUT,
        "check_compatibility": False,
    }

    if settings.qdrant_port:
        kwargs["port"] = settings.qdrant_port

    # Basic auth
    username = QDRANT_BASIC_USER
    password = QDRANT_BASIC_PASSWORD

    # If username is set but no password, fall back to API key as password
    if username and not password and api_key:
        password = api_key

    headers: Dict[str, str] = {}
    if username and password:
        headers["Authorization"] = _basic_authorization_header(username, password)
    if headers:
        kwargs["headers"] = headers

    # API key
    key = api_key or QDRANT_API_KEY
    if key and QDRANT_SEND_API_KEY:
        kwargs["api_key"] = key

    return kwargs


def get_qdrant_client(url: Optional[str] = None, api_key: Optional[str] = None) -> QdrantClient:
    """Thread-safe cached Qdrant client. Recreated when url/api_key changes."""
    global _client, _client_key

    resolved = (url or QDRANT_URL).strip().rstrip("/")
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
