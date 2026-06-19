"""
Fund Service — fetches fund data from the investment bot API.
"""

import json
from typing import Optional

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL, FUND_API_URL, ALL_FUNDS_API_URL
from app.utils.api_client import make_get_request
from app.utils.logger import get_logger

logger = get_logger("fund_service")


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def get_fund_details(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get details for a specific fund by name."""
    logger.info(f"Getting fund details for: {fund_name}")
    url = f"{FUND_API_URL}?fundName={fund_name}"
    if insurer_name:
        url += f"&insurerName={insurer_name}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_plan_fund_performance(plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
    """Get ranked fund performance for a plan."""
    logger.info(f"Getting fund performance for plan: {plan_name}")
    url = f"{FUND_API_URL}?planName={plan_name}&topN={top_n}"
    if insurer_name:
        url += f"&insurerName={insurer_name}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_fund_asset_class_breakup(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get asset class breakup for a fund."""
    logger.info(f"Getting asset class breakup for: {fund_name}")
    url = f"{FUND_API_URL}?fundName={fund_name}&breakupType=assetClass"
    if insurer_name:
        url += f"&insurerName={insurer_name}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_fund_holding_sector_breakup(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get sector-wise holding breakup for a fund."""
    logger.info(f"Getting sector breakup for: {fund_name}")
    url = f"{FUND_API_URL}?fundName={fund_name}&breakupType=sector"
    if insurer_name:
        url += f"&insurerName={insurer_name}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_insurer_top_funds(insurer_name: str, top_n: int = 5) -> str:
    """Get top performing funds for a specific insurer."""
    logger.info(f"Getting top {top_n} funds for insurer: {insurer_name}")
    url = f"{FUND_API_URL}?insurerName={insurer_name}&topN={top_n}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_plan_funds_split_by_type(plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
    """Get funds split into active/passive categories for a plan."""
    logger.info(f"Getting funds split by type for plan: {plan_name}")
    url = f"{FUND_API_URL}?planName={plan_name}&splitByType=true&topN={top_n}"
    if insurer_name:
        url += f"&insurerName={insurer_name}"
    response = await make_get_request(url=url, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def compare_funds(fund_name_1: str, fund_name_2: str, insurer_name_1: Optional[str] = None, insurer_name_2: Optional[str] = None) -> str:
    """Compare two funds side by side."""
    logger.info(f"Comparing funds: {fund_name_1} vs {fund_name_2}")
    # Fetch both funds
    fund1 = await get_fund_details(fund_name_1, insurer_name_1)
    fund2 = await get_fund_details(fund_name_2, insurer_name_2)
    return json.dumps({"fund_1": json.loads(fund1), "fund_2": json.loads(fund2)}, default=str)
