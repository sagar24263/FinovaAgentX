"""
Insurer Service — fetches insurer data from the investment bot API.
"""

import json
from typing import Optional

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.logger import get_logger

logger = get_logger("insurer_service")

INSURER_MASTER_URL = f"{INVESTMENT_API_BASE_URL}/bot/GetInsurerMaster"


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def get_insurer_info(insurer_name: str) -> str:
    """Get information about an insurer."""
    logger.info(f"Getting insurer info for: {insurer_name}")
    response = await make_get_request(
        url=INSURER_MASTER_URL,
        headers=_get_bot_headers(),
    )

    if "error" in response:
        return json.dumps({"error": response["error"]})

    # Filter for the matching insurer
    return_value = response.get("ReturnValue", [])
    if isinstance(return_value, list):
        for insurer in return_value:
            name = insurer.get("InsurerName", "")
            if insurer_name.lower() in name.lower():
                return json.dumps(insurer, default=str)
        return json.dumps({"error": f"Insurer '{insurer_name}' not found"})

    return json.dumps(return_value, default=str)
