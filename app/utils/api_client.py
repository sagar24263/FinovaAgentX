from typing import Any, Dict, Optional, Union

import httpx

from app.utils.logger import get_logger

logger = get_logger("api_client")


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------

async def make_get_request(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Async GET request, returns JSON or error dict."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers or {})
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"data": response.text}
    except httpx.TimeoutException as e:
        logger.error(f"GET timeout for {url}: {e}")
        return {"error": f"Request timed out: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"GET {url} failed with {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}: {e}"}
    except Exception as e:
        logger.error(f"GET {url} error: {e}")
        return {"error": str(e)}


async def make_post_request(
    url: str,
    json_data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """Async POST request (JSON body), returns JSON or error dict."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=json_data, headers=headers or {})
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                return {"data": response.text}
    except httpx.TimeoutException as e:
        logger.error(f"POST timeout for {url}: {e}")
        return {"error": f"Request timed out: {e}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"POST {url} failed with {e.response.status_code}")
        return {"error": f"HTTP {e.response.status_code}: {e}"}
    except Exception as e:
        logger.error(f"POST {url} error: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------

def make_sync_get_request(url: str, headers: dict | None = None) -> dict:
    """Synchronous GET request, returns JSON or error dict."""
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers or {})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for {url}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Request failed for {url}: {e}")
        return {"error": str(e)}
