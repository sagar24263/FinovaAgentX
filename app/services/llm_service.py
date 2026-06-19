"""
LLM Service — Gemini only (via service account credentials).
"""

from google.oauth2 import service_account
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config.env import (
    GEMINI_PROJECT_ID,
    GEMINI_CLIENT_EMAIL,
    GEMINI_CLIENT_ID,
    GEMINI_AUTH_URI,
    GEMINI_TOKEN_URI,
    GEMINI_AUTH_PROVIDER_CERT_URL,
    GEMINI_CLIENT_CERT_URL,
    GEMINI_UNIVERSE_DOMAIN,
    GEMINI_PRIVATE_KEY_ID,
    GEMINI_PRIVATE_KEY,
)
from app.utils.logger import get_logger

logger = get_logger("llm_service")


class LLMService:
    """Centralized Gemini LLM service with caching."""

    def __init__(self):
        self._cache: dict = {}
        self._credentials = self._build_credentials()

    def _build_credentials(self):
        """Build Google service account credentials with proper scopes."""
        if not GEMINI_PRIVATE_KEY or not GEMINI_PROJECT_ID:
            logger.warning("Gemini credentials not configured")
            return None

        private_key = GEMINI_PRIVATE_KEY.replace("\\\\n", "\n").replace("\\n", "\n")

        credentials_dict = {
            "type": "service_account",
            "project_id": GEMINI_PROJECT_ID,
            "private_key_id": GEMINI_PRIVATE_KEY_ID,
            "private_key": private_key,
            "client_email": GEMINI_CLIENT_EMAIL,
            "client_id": GEMINI_CLIENT_ID,
            "auth_uri": GEMINI_AUTH_URI,
            "token_uri": GEMINI_TOKEN_URI,
            "auth_provider_x509_cert_url": GEMINI_AUTH_PROVIDER_CERT_URL,
            "client_x509_cert_url": GEMINI_CLIENT_CERT_URL,
            "universe_domain": GEMINI_UNIVERSE_DOMAIN,
        }

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict, scopes=scopes
        )
        return credentials

    def get_llm(
        self,
        model: str = "gemini-3.1-flash-lite",
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> ChatGoogleGenerativeAI:
        """Get a cached Gemini LLM instance."""
        cache_key = f"{model}_{temperature}_{max_tokens}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._credentials:
            raise ValueError("Gemini credentials not configured")

        llm = ChatGoogleGenerativeAI(
            model=model,
            credentials=self._credentials,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30,
        )

        self._cache[cache_key] = llm
        logger.info(f"Gemini LLM initialized: model={model}, temp={temperature}")
        return llm


# Singleton
_llm_service = LLMService()


def get_llm_service() -> LLMService:
    return _llm_service
