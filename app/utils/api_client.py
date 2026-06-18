import httpx

from app.utils.logger import get_logger

logger = get_logger("api_client")


def make_sync_get_request(url: str, headers: dict | None = None) -> dict:
    """Make a synchronous GET request and return the JSON response."""
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
