"""
Plan Service — plan search and matching.
"""

import time
from typing import Any, Dict, Optional

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.fuzzy_matcher import find_top_matches, insurer_score
from app.utils.logger import get_logger

logger = get_logger("plan_service")

PLAN_MASTER_URL = f"{INVESTMENT_API_BASE_URL}/bot/GetPlanMaster"

_plan_cache: Optional[Dict[str, Any]] = None
_plan_cache_ts = 0.0
PLAN_CACHE_TTL = 900


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def get_plans_master() -> Dict[str, Any]:
    """Get all plans with caching."""
    global _plan_cache, _plan_cache_ts

    now = time.time()
    if _plan_cache and (now - _plan_cache_ts) < PLAN_CACHE_TTL:
        return _plan_cache

    response = await make_get_request(url=PLAN_MASTER_URL, headers=_get_bot_headers())
    if "error" not in response:
        _plan_cache = response
        _plan_cache_ts = now

    return response


async def search_plans_by_name(plan_name: str, insurer_name: Optional[str] = None) -> Dict[str, Any]:
    """Search plans by name with fuzzy matching."""
    if not plan_name or not plan_name.strip():
        return {"error": "Plan name is required."}

    logger.info(f"Searching plan: '{plan_name}' insurer={insurer_name}")

    response = await get_plans_master()
    if "error" in response:
        return response
    if response.get("HasError", False):
        return {"error": "Failed to fetch plans data."}

    plans = response.get("ReturnValue", [])
    if not isinstance(plans, list):
        return {"error": "Invalid plans data format"}

    candidates = [p for p in plans if isinstance(p, dict) and p.get("PlanName")]

    # Pre-filter by insurer
    if insurer_name:
        filtered = [
            p for p in candidates
            if insurer_score(insurer_name.lower(), str(p.get("InsurerName", "")).lower()) >= 75
        ]
        if filtered:
            candidates = filtered

    results = find_top_matches(
        query=plan_name.strip(),
        candidates=candidates,
        get_name=lambda p: p.get("PlanName", ""),
        threshold=55.0,
        top_k=5,
        insurer_query=insurer_name,
        get_insurer=lambda p: p.get("InsurerName", ""),
    )

    if not results:
        return {"HasError": False, "ReturnValue": []}

    return {"HasError": False, "ReturnValue": [entry for entry, score in results]}
