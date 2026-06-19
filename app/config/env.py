import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from app.utils.logger import get_logger

logger = get_logger("env")

# ---------------------------------------------------------------------------
# Load the correct env file based on ENV variable
# ---------------------------------------------------------------------------
ENV = os.getenv("ENV", "dev")
_env_file = os.path.join(os.path.dirname(__file__), "..", "..", f"env.{ENV}")
load_dotenv(_env_file, override=True)

# ---------------------------------------------------------------------------
# Now import secret_manager (it uses os.getenv which is populated by dotenv)
# ---------------------------------------------------------------------------
from app.config.secret_manager import get_secret_manager  # noqa: E402

# AWS Secret Manager configuration
USE_SECRET_MANAGER = os.getenv("USE_SECRET_MANAGER", "true").lower() == "true"

# Cache for the entire secret JSON
_secret_cache: Optional[Dict[str, Any]] = None


def get_config_value(key: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
    """
    Get configuration value from AWS Secret Manager or environment variables.
    Uses caching to avoid repeated secret manager calls.

    Args:
        key: The key to retrieve from secret manager
        fallback_env_var: Fallback environment variable name

    Returns:
        Configuration value or None
    """
    global _secret_cache

    if _secret_cache and key in _secret_cache:
        return _secret_cache[key]

    if USE_SECRET_MANAGER:
        try:
            if _secret_cache is None:
                sm = get_secret_manager()
                _secret_cache = sm.get_secret()
                logger.info(f"Loaded {len(_secret_cache)} values from Secret Manager")

            if key in _secret_cache:
                return _secret_cache[key]
            else:
                logger.warning(f"Key '{key}' not found in Secret Manager")

        except Exception as e:
            logger.warning(f"Failed to get '{key}' from Secret Manager: {e}")
            _secret_cache = {}

    # Fallback to environment variables
    if fallback_env_var:
        return os.getenv(fallback_env_var)
    return os.getenv(key.upper())


def preload_configuration():
    """Preload all configuration values from Secret Manager at startup."""
    if not USE_SECRET_MANAGER:
        logger.info("Secret Manager disabled, skipping preload")
        return

    logger.info("Preloading configuration from Secret Manager...")
    try:
        sm = get_secret_manager()
        global _secret_cache
        _secret_cache = sm.get_secret()
        logger.info(f"Preloaded {len(_secret_cache)} configuration values")
    except Exception as e:
        logger.error(f"Failed to preload configuration: {e}")
        _secret_cache = {}


def clear_config_cache():
    """Clear the configuration cache."""
    global _secret_cache
    _secret_cache = None
    logger.info("Configuration cache cleared")


# ---------------------------------------------------------------------------
# Preload at module import
# ---------------------------------------------------------------------------
preload_configuration()

# ---------------------------------------------------------------------------
# Azure OpenAI
# ---------------------------------------------------------------------------
AZURE_OPENAI_API_KEY = get_config_value("AzureOpenAIApiKey")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
INVESTMENT_AGENT_API_KEY = get_config_value("InvestmentAgentApiKey")
API_KEYS_CONFIG_RAW = get_config_value("ApiKeysConfig")
API_KEYS_CONFIG = (
    json.loads(API_KEYS_CONFIG_RAW)
    if API_KEYS_CONFIG_RAW and isinstance(API_KEYS_CONFIG_RAW, str)
    else (API_KEYS_CONFIG_RAW if API_KEYS_CONFIG_RAW else {})
)
BOT_HEADER_TOKEN = get_config_value("BotHeaderToken")

# ---------------------------------------------------------------------------
# Gemini (env vars + secrets)
# ---------------------------------------------------------------------------
GEMINI_PROJECT_ID = os.getenv("GEMINI_PROJECT_ID")
GEMINI_CLIENT_EMAIL = os.getenv("GEMINI_CLIENT_EMAIL")
GEMINI_CLIENT_ID = os.getenv("GEMINI_CLIENT_ID")
GEMINI_AUTH_URI = os.getenv("GEMINI_AUTH_URI")
GEMINI_TOKEN_URI = os.getenv("GEMINI_TOKEN_URI")
GEMINI_AUTH_PROVIDER_CERT_URL = os.getenv("GEMINI_AUTH_PROVIDER_CERT_URL")
GEMINI_CLIENT_CERT_URL = os.getenv("GEMINI_CLIENT_CERT_URL")
GEMINI_UNIVERSE_DOMAIN = os.getenv("GEMINI_UNIVERSE_DOMAIN")
GEMINI_PRIVATE_KEY_ID = get_config_value("gemini_private_key_id")
GEMINI_PRIVATE_KEY = get_config_value("gemini_private_key")

# ---------------------------------------------------------------------------
# API URLs
# ---------------------------------------------------------------------------
INVESTMENT_API_BASE_URL = os.getenv("INVESTMENT_API_BASE_URL", "")
FUND_API_BASE_URL = os.getenv("FUND_API_BASE_URL", "")
FUND_API_URL = f"{FUND_API_BASE_URL}/Fund/GetPlanFundPerformanceData"
ALL_FUNDS_API_URL = f"{FUND_API_BASE_URL}/Fund/GetAllFundsAndPlans"
TERM_API_BASE_URL = os.getenv("TERM_API_BASE_URL", "")
PENSION_API_BASE_URL = os.getenv("PENSION_API_BASE_URL", "")
NFO_TIMELINE_API_URL = os.getenv("NFO_TIMELINE_API_URL", "")
NFO_TIMELINE_TIMEOUT = float(os.getenv("NFO_TIMELINE_TIMEOUT", "30"))

# ---------------------------------------------------------------------------
# DocumentDB (Savings DB)
# ---------------------------------------------------------------------------
SAVINGS_DB_USER = get_config_value("SavingsDBUser")
SAVINGS_DB_PASSWORD = get_config_value("SavingsDBPassword")
DOCUMENTDB_HOST = os.getenv("DOCUMENTDB_HOST", "")
SAVINGS_DB_NAME = os.getenv("SAVINGS_DB_NAME", "savingsDB")
SAVINGS_DB_URI = (
    f"mongodb://{SAVINGS_DB_USER}:{SAVINGS_DB_PASSWORD}@{DOCUMENTDB_HOST}/{SAVINGS_DB_NAME}"
    f"?replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false"
)

# ---------------------------------------------------------------------------
# Qdrant
# ---------------------------------------------------------------------------
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_BASIC_USER = get_config_value("finovaVectorDBUsername", "QDRANT_BASIC_USER")
QDRANT_BASIC_PASSWORD = get_config_value("finovaVectorDBPassword", "QDRANT_BASIC_PASSWORD")

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
REDIS_ENDPOINT = os.getenv("REDIS_ENDPOINT", "")
