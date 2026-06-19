import json
from typing import Any, Dict

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.logger import get_logger

logger = get_logger("nfo_service")

ACTIVE_NFOS_URL = f"{INVESTMENT_API_BASE_URL}/bot/GetActiveNfos"


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def get_active_nfos() -> str:
    """
    Fetch all currently active NFOs across product lanes (Ml, Pension, Gift).
    Returns raw JSON string for the LLM to interpret.
    """
    try:
        response = await make_get_request(
            url=ACTIVE_NFOS_URL,
            headers=_get_bot_headers(),
        )

        if "error" in response:
            logger.error(f"Failed to get active NFOs: {response['error']}")
            return json.dumps({"error": response["error"]})

        if response.get("HasError", True):
            logger.error("GetActiveNfos returned HasError=true")
            return json.dumps({"error": "Failed to fetch active NFOs from the API."})

        return_value = response.get("ReturnValue", {})
        return json.dumps(return_value, default=str)

    except Exception as e:
        logger.error(f"Error getting active NFOs: {e}")
        return json.dumps({"error": str(e)})
