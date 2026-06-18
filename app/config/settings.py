import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # App
    env: str = "dev"
    app_name: str = "FastAPI App"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    # AWS Secret Manager
    use_secret_manager: bool = False
    aws_region: str = "ap-south-1"
    aws_secret_name: str = "QA_Investment"
    local_aws_token: str = ""

    # DocumentDB (Savings DB)
    documentdb_host: str = ""
    savings_db_name: str = ""

    # Redis
    redis_endpoint: str = ""

    # Qdrant
    qdrant_url: str = ""
    qdrant_port: int = 443
    qdrant_basic_user: str = ""


@lru_cache()
def get_settings() -> Settings:
    """Load settings once and cache. Reads ENV from environment variable."""
    env = os.getenv("ENV", "dev")
    env_file = BASE_DIR / f"env.{env}"
    return Settings(_env_file=str(env_file))
