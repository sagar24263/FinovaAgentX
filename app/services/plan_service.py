import asyncio
from typing import Any, Dict, Optional

from async_lru import alru_cache

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.fuzzy_matcher import fuzzy_score
from app.utils.logger import get_logger

_logger = get_logger("plan_service")

ENDPOINTS = {
    "top_plans": f"{INVESTMENT_API_BASE_URL}/bot/GetTopPlans",
    "plan_info": f"{INVESTMENT_API_BASE_URL}/bot/GetPlanInfo",
    "plan_master": f"{INVESTMENT_API_BASE_URL}/bot/GetPlanMaster",
    "insurer_master": f"{INVESTMENT_API_BASE_URL}/bot/GetInsurerMaster",
}


def get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN,
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


async def _make_api_call(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return await make_get_request(
        url=endpoint,
        params=params,
        headers=get_bot_headers(),
    )


async def get_top_plans() -> Dict[str, Any]:
    return await _make_api_call(ENDPOINTS["top_plans"])


async def get_plan_details(plan_name: str, insurer_name: Optional[str] = None) -> Dict[str, Any]:
    if not plan_name:
        return {"error": "Plan name is required."}

    _logger.info(f"Fetching plan details for: '{plan_name}'")

    matched_response = await search_plans_by_name(plan_name, insurer_name)

    if "error" in matched_response:
        return matched_response

    matches = matched_response.get("ReturnValue", [])
    if not matches:
        return {"error": "No matching plan found."}

    best_plan_id = matches[0].get("PlanID")
    if not best_plan_id:
        return {"error": "Top match has no plan name."}

    return await _make_api_call(ENDPOINTS["plan_info"], params={"planID": best_plan_id})


@alru_cache(maxsize=1, ttl=900)
async def get_plans_master() -> Dict[str, Any]:
    return await _make_api_call(ENDPOINTS["plan_master"])


@alru_cache(maxsize=1, ttl=900)
async def get_insurer_master() -> Dict[str, Any]:
    return await _make_api_call(ENDPOINTS["insurer_master"])


async def get_insurer_info(insurer_name: str) -> Dict[str, Any]:
    try:
        if not insurer_name or not insurer_name.strip():
            return {"error": "Insurer name is required"}

        _logger.info(f"Searching for insurer: '{insurer_name}'")

        insurers_response = await get_insurer_master()

        if "error" in insurers_response:
            return insurers_response

        if insurers_response.get("HasError", True):
            error_msg = "Failed to fetch insurer master data"
            _logger.error(error_msg)
            return {"error": error_msg}

        insurers = insurers_response.get("ReturnValue", [])
        if not isinstance(insurers, list):
            return {"error": "Invalid insurers data format"}

        matching_insurers = []
        clean_query = insurer_name.lower().strip()

        for insurer in insurers:
            if not isinstance(insurer, dict):
                continue

            insurer_name_from_data = insurer.get("InsurerName", "")
            if not insurer_name_from_data:
                continue

            insurer_name_lower = insurer_name_from_data.lower().strip()
            combined_score = fuzzy_score(clean_query, insurer_name_lower)

            if combined_score > 60:
                insurer_with_score = insurer.copy()
                insurer_with_score["_match_score"] = combined_score
                matching_insurers.append(insurer_with_score)

        if matching_insurers:
            matching_insurers.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
            for ins in matching_insurers:
                ins.pop("_match_score", None)

            return {
                "HasError": False,
                "ReturnValue": matching_insurers,
            }

        _logger.info(f"No matching insurer found for: '{insurer_name}'")
        return {
            "HasError": False,
            "ReturnValue": [],
        }

    except Exception as e:
        _logger.error(f"Insurer search failed: {str(e)}", exc_info=True)
        return {"error": f"Insurer search failed: {str(e)}"}


async def compare_plans(
    plan_name1: str,
    plan_name2: str,
    insurer_name1: Optional[str] = None,
    insurer_name2: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        if not plan_name1 or not plan_name1.strip():
            return {"error": "First plan name is required"}

        if not plan_name2 or not plan_name2.strip():
            return {"error": "Second plan name is required"}

        _logger.info(f"Comparing plans: '{plan_name1}' vs '{plan_name2}'")

        plan1_task = get_plan_details(plan_name1, insurer_name1)
        plan2_task = get_plan_details(plan_name2, insurer_name2)

        plan1_response, plan2_response = await asyncio.gather(plan1_task, plan2_task)

        if "error" in plan1_response:
            return {"error": f"Failed to fetch plan1 '{plan_name1}': {plan1_response['error']}"}

        if "error" in plan2_response:
            return {"error": f"Failed to fetch plan2 '{plan_name2}': {plan2_response['error']}"}

        if plan1_response.get("HasError", True):
            return {"error": f"API error fetching plan1 '{plan_name1}'"}

        if plan2_response.get("HasError", True):
            return {"error": f"API error fetching plan2 '{plan_name2}'"}

        plan1_data = plan1_response.get("ReturnValue", {})
        plan2_data = plan2_response.get("ReturnValue", {})

        if not plan1_data:
            return {"error": f"No data found for plan1 '{plan_name1}'"}

        if not plan2_data:
            return {"error": f"No data found for plan2 '{plan_name2}'"}

        return {
            "HasError": False,
            "ReturnValue": {
                "plan1": {
                    "searched_name": plan_name1,
                    "insurer_filter": insurer_name1,
                    "plan_details": plan1_data,
                },
                "plan2": {
                    "searched_name": plan_name2,
                    "insurer_filter": insurer_name2,
                    "plan_details": plan2_data,
                },
            },
        }

    except Exception as e:
        _logger.error(f"Plan comparison failed: {str(e)}", exc_info=True)
        return {"error": f"Plan comparison failed: {str(e)}"}


async def get_plans_by_insurer(insurer_name: str, count: Optional[int] = 3) -> Dict[str, Any]:
    try:
        if not insurer_name or not insurer_name.strip():
            return {"error": "Insurer name is required"}

        if count is not None and (count <= 0 or count > 50):
            return {"error": "Count must be between 1 and 50"}

        _logger.info(f"Fetching plans for insurer: '{insurer_name}'")

        all_plans_response = await get_plans_master()

        if "error" in all_plans_response:
            return all_plans_response

        if all_plans_response.get("HasError", True):
            return {"error": "Failed to fetch plans data"}

        plans = all_plans_response.get("ReturnValue", [])
        if not isinstance(plans, list):
            return {"error": "Invalid plans data format"}

        matching_plans = []
        clean_query = insurer_name.lower().strip()

        for plan in plans:
            if not isinstance(plan, dict):
                continue

            insurer_name_from_data = plan.get("InsurerName", "")
            if not insurer_name_from_data:
                continue

            insurer_name_lower = insurer_name_from_data.lower().strip()
            combined_score = fuzzy_score(clean_query, insurer_name_lower)

            if combined_score > 60:
                plan_with_score = plan.copy()
                plan_with_score["_match_score"] = combined_score
                matching_plans.append(plan_with_score)

        if matching_plans:
            matching_plans.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
            top_plans = matching_plans[:count]
            plan_names = [plan.get("PlanName", "Unknown Plan") for plan in top_plans]

            _logger.info(
                f"Found {len(matching_plans)} plans for insurer '{insurer_name}', returning top {count}"
            )
            return {
                "HasError": False,
                "ReturnValue": plan_names,
            }

        _logger.info(f"No plans found for insurer: '{insurer_name}'")
        return {
            "HasError": False,
            "ReturnValue": [],
        }

    except Exception as e:
        _logger.error(f"Get plans by insurer failed: {str(e)}", exc_info=True)
        return {"error": f"Get plans by insurer failed: {str(e)}"}


async def search_plans_by_name(plan_name: str, insurer_name: Optional[str] = None) -> Dict[str, Any]:
    try:
        log_message = f"Smart Searching for plan: '{plan_name}'"
        if insurer_name:
            log_message += f" from Insurer: '{insurer_name}'"
        _logger.info(log_message)

        all_plans_response = await get_plans_master()

        if "error" in all_plans_response:
            return all_plans_response

        plans = all_plans_response.get("ReturnValue", [])
        if not isinstance(plans, list):
            return {"error": "Invalid plans data format"}

        matching_plans = []
        clean_query = plan_name.lower().strip()
        normalized_search_insurer = insurer_name.lower().strip() if insurer_name else None

        if normalized_search_insurer and normalized_search_insurer in clean_query:
            clean_query = clean_query.replace(normalized_search_insurer, "").strip()

        for plan in plans:
            if not isinstance(plan, dict):
                continue

            plan_name_from_data = plan.get("PlanName", "")
            if not plan_name_from_data:
                continue

            if normalized_search_insurer:
                insurer_name_from_data = str(plan.get("InsurerName", ""))
                if normalized_search_insurer not in insurer_name_from_data.lower().strip():
                    continue

            plan_name_lower = plan_name_from_data.lower()
            insurer_name_from_data = str(plan.get("InsurerName", "")).lower()
            if insurer_name_from_data in plan_name_lower:
                plan_name_lower = plan_name_lower.replace(insurer_name_from_data, "").strip()

            combined_score = fuzzy_score(clean_query, plan_name_lower)

            if combined_score > 65:
                plan_with_score = plan.copy()
                plan_with_score["_match_score"] = combined_score
                matching_plans.append(plan_with_score)

        if matching_plans:
            matching_plans.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
            for p in matching_plans:
                p.pop("_match_score", None)

            return {"HasError": False, "ReturnValue": matching_plans}

        return {"HasError": False, "ReturnValue": []}

    except Exception as e:
        _logger.error(f"Search failed: {str(e)}", exc_info=True)
        return {"error": f"Search failed: {str(e)}"}
