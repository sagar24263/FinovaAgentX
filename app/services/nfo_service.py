"""
NFO Service — fetches NFO data from the investment bot API.
"""

import json
from typing import Optional

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL, NFO_TIMELINE_API_URL
from app.utils.api_client import make_get_request, make_post_request
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
    logger.info(f"Calling active NFOs API: {ACTIVE_NFOS_URL}")
    logger.info(f"BOT_HEADER_TOKEN present: {bool(BOT_HEADER_TOKEN)}")

    try:
        response = await make_get_request(
            url=ACTIVE_NFOS_URL,
            headers=_get_bot_headers(),
        )

        logger.info(f"API response keys: {list(response.keys()) if isinstance(response, dict) else type(response)}")

        if "error" in response:
            logger.error(f"Failed to get active NFOs: {response['error']}")
            return json.dumps({"error": response["error"]})

        if response.get("HasError", True):
            logger.error("GetActiveNfos returned HasError=true")
            return json.dumps({"error": "Failed to fetch active NFOs from the API."})

        return_value = response.get("ReturnValue", {})
        return json.dumps(return_value, default=str)

    except Exception as e:
        logger.error(f"Error getting active NFOs: {type(e).__name__}: {e}")
        return json.dumps({"error": str(e)})


async def get_nfo_timeline(insurer_name: Optional[str] = None, start_month: str = "January-2023", end_month: str = "December-2027") -> str:
    """Fetch NFO timeline from CMS API."""
    logger.info(f"Getting NFO timeline: insurer={insurer_name}, range={start_month} to {end_month}")

    payload = {
        "StartMonth": start_month,
        "EndMonth": end_month,
    }

    response = await make_post_request(
        url=NFO_TIMELINE_API_URL,
        json_data=payload,
        headers=_get_bot_headers(),
    )

    if "error" in response:
        return json.dumps({"error": response["error"]})

    # Filter by insurer if specified
    data = response.get("ReturnValue", response)
    if insurer_name and isinstance(data, list):
        data = [item for item in data if insurer_name.lower() in str(item.get("InsurerName", "")).lower()]

    return json.dumps(data, default=str)


async def get_nfo_listing_returns(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Look up listing returns for a specific NFO fund."""
    logger.info(f"Getting NFO listing returns for: {fund_name}")

    # Get timeline data and search for the fund
    timeline_data = await get_nfo_timeline(insurer_name)
    items = json.loads(timeline_data)

    if isinstance(items, dict) and "error" in items:
        return timeline_data

    if isinstance(items, list):
        for item in items:
            item_fund = item.get("FundName", "")
            if fund_name.lower() in item_fund.lower():
                return json.dumps(item, default=str)

    return json.dumps({"error": f"No listing returns found for '{fund_name}'"})


async def get_closed_funds(insurer_name: Optional[str] = None, fund_name: Optional[str] = None) -> str:
    """Check which NFO funds are closed for subscription."""
    logger.info(f"Getting closed funds: insurer={insurer_name}, fund={fund_name}")

    # TODO: Implement from closed_funds.json or API when available
    return json.dumps({"message": "Closed funds data not yet configured."})
