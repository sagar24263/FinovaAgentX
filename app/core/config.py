from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    app_name: str = "FastAPI App"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"


def get_settings(env: str = "dev") -> Settings:
    env_file = BASE_DIR / f"env.{env}"
    return Settings(_env_file=str(env_file))
