"""
Plan Service — plan and insurer search, comparison, details.
"""

import asyncio
import json
import time
from typing import Any, Dict, Optional

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.fuzzy_matcher import fuzzy_score
from app.utils.logger import get_logger

logger = get_logger("plan_service")

ENDPOINTS = {
    "top_plans": f"{INVESTMENT_API_BASE_URL}/bot/GetTopPlans",
    "plan_info": f"{INVESTMENT_API_BASE_URL}/bot/GetPlanInfo",
    "plan_master": f"{INVESTMENT_API_BASE_URL}/bot/GetPlanMaster",
    "insurer_master": f"{INVESTMENT_API_BASE_URL}/bot/GetInsurerMaster",
}

_plan_cache: Optional[Dict[str, Any]] = None
_plan_cache_ts = 0.0
_insurer_cache: Optional[Dict[str, Any]] = None
_insurer_cache_ts = 0.0
CACHE_TTL = 900


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def _api_call(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return await make_get_request(url=endpoint, params=params, headers=_get_bot_headers())


# ---------------------------------------------------------------------------
# Cached master data
# ---------------------------------------------------------------------------


async def get_plans_master() -> Dict[str, Any]:
    global _plan_cache, _plan_cache_ts
    now = time.time()
    if _plan_cache and (now - _plan_cache_ts) < CACHE_TTL:
        return _plan_cache
    response = await _api_call(ENDPOINTS["plan_master"])
    if "error" not in response:
        _plan_cache = response
        _plan_cache_ts = now
    return response


async def get_insurer_master() -> Dict[str, Any]:
    global _insurer_cache, _insurer_cache_ts
    now = time.time()
    if _insurer_cache and (now - _insurer_cache_ts) < CACHE_TTL:
        return _insurer_cache
    response = await _api_call(ENDPOINTS["insurer_master"])
    if "error" not in response:
        _insurer_cache = response
        _insurer_cache_ts = now
    return response


# ---------------------------------------------------------------------------
# Plan search (fuzzy)
# ---------------------------------------------------------------------------


async def search_plans_by_name(plan_name: str, insurer_name: Optional[str] = None) -> Dict[str, Any]:
    if not plan_name or not plan_name.strip():
        return {"error": "Plan name is required."}

    logger.info(f"Searching plan: '{plan_name}' insurer={insurer_name}")

    response = await get_plans_master()
    if "error" in response:
        return response
    if response.get("HasError", True):
        return {"error": "Failed to fetch plans data."}

    plans = response.get("ReturnValue", [])
    if not isinstance(plans, list):
        return {"error": "Invalid plans data format"}

    candidates = [p for p in plans if isinstance(p, dict) and p.get("PlanName")]
    clean_query = plan_name.lower().strip()
    normalized_insurer = insurer_name.lower().strip() if insurer_name else None

    if normalized_insurer and normalized_insurer in clean_query:
        clean_query = clean_query.replace(normalized_insurer, "").strip()

    if normalized_insurer:
        filtered = [p for p in candidates if normalized_insurer in str(p.get("InsurerName", "")).lower()]
        if filtered:
            candidates = filtered

    matching = []
    for plan in candidates:
        plan_name_data = plan.get("PlanName", "").lower()
        insurer_in_plan = str(plan.get("InsurerName", "")).lower()
        if insurer_in_plan in plan_name_data:
            plan_name_data = plan_name_data.replace(insurer_in_plan, "").strip()

        score = fuzzy_score(clean_query, plan_name_data)
        if score > 60:
            matching.append((plan, score))

    matching.sort(key=lambda x: x[1], reverse=True)
    if not matching:
        return {"HasError": False, "ReturnValue": []}

    return {"HasError": False, "ReturnValue": [p for p, s in matching[:5]]}


# ---------------------------------------------------------------------------
# Top plans
# ---------------------------------------------------------------------------


async def get_top_plans() -> str:
    response = await _api_call(ENDPOINTS["top_plans"])
    return json.dumps(response, default=str)


# ---------------------------------------------------------------------------
# Plan details
# ---------------------------------------------------------------------------


async def get_plan_details(plan_name: str, insurer_name: Optional[str] = None) -> str:
    if not plan_name:
        return json.dumps({"error": "Plan name is required."})

    logger.info(f"Getting plan details for: '{plan_name}'")
    matched = await search_plans_by_name(plan_name, insurer_name)
    if "error" in matched:
        return json.dumps(matched)

    matches = matched.get("ReturnValue", [])
    if not matches:
        return json.dumps({"error": f"No matching plan found for '{plan_name}'."})

    plan_id = matches[0].get("PlanID")
    if not plan_id:
        return json.dumps({"error": "Plan has no ID."})

    response = await _api_call(ENDPOINTS["plan_info"], params={"planID": plan_id})
    return json.dumps(response, default=str)


# ---------------------------------------------------------------------------
# Compare plans
# ---------------------------------------------------------------------------


async def compare_plans(plan_name1: str, plan_name2: str, insurer_name1: Optional[str] = None, insurer_name2: Optional[str] = None) -> str:
    if not plan_name1 or not plan_name2:
        return json.dumps({"error": "Both plan names are required."})

    logger.info(f"Comparing: '{plan_name1}' vs '{plan_name2}'")
    plan1_task = get_plan_details(plan_name1, insurer_name1)
    plan2_task = get_plan_details(plan_name2, insurer_name2)
    plan1_result, plan2_result = await asyncio.gather(plan1_task, plan2_task)

    return json.dumps({"plan_1": json.loads(plan1_result), "plan_2": json.loads(plan2_result)}, default=str)


# ---------------------------------------------------------------------------
# Insurer info
# ---------------------------------------------------------------------------


async def get_insurer_info(insurer_name: str) -> str:
    if not insurer_name or not insurer_name.strip():
        return json.dumps({"error": "Insurer name is required"})

    logger.info(f"Searching insurer: '{insurer_name}'")
    response = await get_insurer_master()
    if "error" in response:
        return json.dumps(response)
    if response.get("HasError", True):
        return json.dumps({"error": "Failed to fetch insurer data."})

    insurers = response.get("ReturnValue", [])
    if not isinstance(insurers, list):
        return json.dumps({"error": "Invalid insurer data format"})

    clean_query = insurer_name.lower().strip()
    matching = []
    for insurer in insurers:
        if not isinstance(insurer, dict):
            continue
        name = insurer.get("InsurerName", "")
        if not name:
            continue
        score = fuzzy_score(clean_query, name.lower())
        if score > 60:
            matching.append((insurer, score))

    matching.sort(key=lambda x: x[1], reverse=True)
    if not matching:
        return json.dumps({"error": f"No insurer found matching '{insurer_name}'"})

    return json.dumps(matching[0][0], default=str)


# ---------------------------------------------------------------------------
# Plans by insurer
# ---------------------------------------------------------------------------


async def get_plans_by_insurer(insurer_name: str, count: int = 3) -> str:
    if not insurer_name or not insurer_name.strip():
        return json.dumps({"error": "Insurer name is required"})

    logger.info(f"Getting plans for insurer: '{insurer_name}'")
    response = await get_plans_master()
    if "error" in response:
        return json.dumps(response)

    plans = response.get("ReturnValue", [])
    if not isinstance(plans, list):
        return json.dumps({"error": "Invalid plans data"})

    clean_query = insurer_name.lower().strip()
    matching = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        plan_insurer = str(plan.get("InsurerName", "")).lower()
        score = fuzzy_score(clean_query, plan_insurer)
        if score > 60:
            matching.append(plan.get("PlanName", "Unknown"))

    if not matching:
        return json.dumps({"error": f"No plans found for insurer '{insurer_name}'"})

    return json.dumps({"insurer": insurer_name, "plans": matching[:count]}, default=str)
