import redis as redis_lib

from app.config.env import REDIS_ENDPOINT
from app.utils.logger import get_logger

logger = get_logger("redis")

_redis_client: redis_lib.Redis | None = None


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    """Parse 'host:port' string."""
    if ":" in endpoint:
        host, port = endpoint.rsplit(":", 1)
        return host, int(port)
    return endpoint, 6379


def get_redis_client() -> redis_lib.Redis | None:
    """Get Redis client (singleton). Returns None if unavailable."""
    global _redis_client

    if _redis_client is None:
        if not REDIS_ENDPOINT:
            logger.warning("Redis endpoint not configured")
            return None

        try:
            host, port = _parse_endpoint(REDIS_ENDPOINT)
            _redis_client = redis_lib.Redis(
                host=host,
                port=port,
                decode_responses=True,
            )
            _redis_client.ping()
            logger.info("Redis connection established")
        except redis_lib.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}")
            _redis_client = None
        except Exception as e:
            logger.warning(f"Redis connection error: {e}")
            _redis_client = None

    return _redis_client
