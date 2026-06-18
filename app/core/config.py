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


def get_settings(env: str = "dev") -> Settings:
    env_file = BASE_DIR / f"env.{env}"
    return Settings(_env_file=str(env_file))
