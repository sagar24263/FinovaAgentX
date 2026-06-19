"""
Fund Service — fetches fund data with fuzzy matching.
"""

import json
import time
from typing import Any, Dict, List, Optional

from app.config.env import BOT_HEADER_TOKEN, FUND_API_URL, ALL_FUNDS_API_URL, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request, make_post_request
from app.utils.fuzzy_matcher import fuzzy_score, insurer_score, find_top_matches
from app.utils.logger import get_logger

logger = get_logger("fund_service")

ALL_FUNDS_CACHE_TTL = 900  # 15 min
_all_funds_cache: Optional[Dict[str, Any]] = None
_all_funds_cache_ts = 0.0

INSURER_MATCH_THRESHOLD = 75


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


def _insurer_matches(query_insurer: str, candidate_insurer: str) -> bool:
    q = query_insurer.lower().strip()
    c = candidate_insurer.lower().strip()
    if not q or not c:
        return False
    if q in c or c in q:
        return True
    return insurer_score(q, c) >= INSURER_MATCH_THRESHOLD


# ---------------------------------------------------------------------------
# Master data
# ---------------------------------------------------------------------------

async def get_all_funds_master() -> Dict[str, Any]:
    """Get all funds with caching."""
    global _all_funds_cache, _all_funds_cache_ts

    if not ALL_FUNDS_API_URL:
        return {"error": "ALL_FUNDS_API_URL is not configured."}

    now = time.time()
    if _all_funds_cache and (now - _all_funds_cache_ts) < ALL_FUNDS_CACHE_TTL:
        return _all_funds_cache

    response = await make_get_request(url=ALL_FUNDS_API_URL, headers=_get_bot_headers())
    if "error" not in response:
        _all_funds_cache = response
        _all_funds_cache_ts = now

    return response


async def search_funds_by_name(fund_name: str, insurer_name: Optional[str] = None) -> Dict[str, Any]:
    """Search funds by name using fuzzy matching."""
    if not fund_name or not fund_name.strip():
        return {"error": "Fund name is required."}

    logger.info(f"Searching fund: '{fund_name}' insurer={insurer_name}")

    response = await get_all_funds_master()
    if "error" in response:
        return response
    if response.get("HasError", False):
        return {"error": "Failed to fetch funds master data."}

    funds = response.get("ReturnValue", [])
    if not isinstance(funds, list):
        return {"error": "Invalid funds data format"}

    candidates = [f for f in funds if isinstance(f, dict) and f.get("FundName")]

    # Pre-filter by insurer
    if insurer_name:
        filtered = [f for f in candidates if _insurer_matches(insurer_name, str(f.get("InsurerName", "")))]
        if filtered:
            candidates = filtered

    results = find_top_matches(
        query=fund_name.strip(),
        candidates=candidates,
        get_name=lambda f: f.get("FundName", ""),
        threshold=55.0,
        top_k=10,
        insurer_query=insurer_name,
        get_insurer=lambda f: f.get("InsurerName", ""),
    )

    if not results:
        return {"HasError": False, "ReturnValue": []}

    matching_funds = [entry for entry, score in results]
    return {"HasError": False, "ReturnValue": matching_funds}


# ---------------------------------------------------------------------------
# Fund details
# ---------------------------------------------------------------------------

def _format_fund_details(fund: Dict[str, Any]) -> Dict[str, Any]:
    plans = fund.get("Plans", [])
    formatted_plans = [{"PlanID": p.get("PlanID"), "PlanName": p.get("PlanName")} for p in plans if isinstance(p, dict)]

    result = {
        "FundName": fund.get("FundName"),
        "InsurerName": fund.get("InsurerName"),
        "returns": {
            "1Y": fund.get("OneYrGrowth"),
            "3Y": fund.get("ThreeYrGrowth"),
            "5Y": fund.get("FiveYrGrowth"),
            "7Y": fund.get("Ret7YR"),
            "10Y": fund.get("Ret10YR"),
            "SinceInception": fund.get("RSI"),
        },
        "Plans": formatted_plans,
    }
    if fund.get("BenchMarkFundName"):
        result["benchmark"] = {
            "BenchMarkFundName": fund.get("BenchMarkFundName"),
            "BM_5Y": fund.get("BenchMarkFiveYrGrowth"),
            "BM_7Y": fund.get("BenchMarkRet7YR"),
            "BM_10Y": fund.get("BenchMarkRet10YR"),
        }
    return result


async def get_fund_details(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get details for a specific fund by name with fuzzy matching."""
    logger.info(f"Getting fund details for: {fund_name}")

    matched = await search_funds_by_name(fund_name, insurer_name)
    if "error" in matched:
        return json.dumps(matched)

    matches = matched.get("ReturnValue", [])
    if not matches:
        return json.dumps({"error": f"No matching fund found for '{fund_name}'."})

    # If multiple insurers and no insurer specified, ask for clarification
    if not insurer_name:
        insurers = list({m.get("InsurerName") for m in matches if m.get("InsurerName")})
        if len(insurers) > 1:
            return json.dumps({
                "matched_fund": matches[0].get("FundName"),
                "multiple_insurers": True,
                "available_insurers": sorted(insurers),
                "message": f"This fund is available from multiple insurers: {', '.join(sorted(insurers))}. Which insurer?"
            })

    best = _format_fund_details(matches[0])
    return json.dumps(best, default=str)


async def get_plan_fund_performance(plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
    """Get ranked fund performance for a plan."""
    logger.info(f"Getting fund performance for plan: {plan_name}")

    if not FUND_API_URL:
        return json.dumps({"error": "FUND_API_URL not configured"})

    # First find the plan by name
    from app.services.plan_service import search_plans_by_name
    plan_response = await search_plans_by_name(plan_name, insurer_name)
    if "error" in plan_response:
        return json.dumps(plan_response)

    matches = plan_response.get("ReturnValue", [])
    if not matches:
        return json.dumps({"error": f"No matching plan found for '{plan_name}'."})

    plan_id = matches[0].get("PlanID")
    if not plan_id:
        return json.dumps({"error": "Plan has no ID."})

    # Fetch fund performance by plan ID
    response = await make_post_request(url=FUND_API_URL, json_data={"PlanID": plan_id}, headers=_get_bot_headers())
    if "error" in response:
        return json.dumps(response)

    funds = response.get("Funds", [])
    if not funds:
        return json.dumps({"error": "No funds available for this plan"})

    # Sort by 10Y return
    funds.sort(key=lambda f: f.get("Ret10YR") or 0, reverse=True)
    top_funds = [{"FundName": f.get("FundName"), "5Y": f.get("FiveYrGrowth"), "7Y": f.get("Ret7YR"), "10Y": f.get("Ret10YR")} for f in funds[:top_n]]

    return json.dumps({"plan": matches[0].get("PlanName"), "top_funds": top_funds, "total_funds": len(funds)}, default=str)


async def get_fund_asset_class_breakup(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get asset class breakup for a fund."""
    logger.info(f"Getting asset class breakup for: {fund_name}")

    matched = await search_funds_by_name(fund_name, insurer_name)
    matches = matched.get("ReturnValue", [])
    if not matches:
        return json.dumps({"error": f"No matching fund found for '{fund_name}'."})

    fund_id = matches[0].get("FundID")
    url = f"{INVESTMENT_API_BASE_URL}/enqapi/Quote/GetFundHoldingAssetClassBreakup"
    response = await make_get_request(url=url, params={"VRFundID": fund_id}, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_fund_holding_sector_breakup(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Get sector-wise holding breakup for a fund."""
    logger.info(f"Getting sector breakup for: {fund_name}")

    matched = await search_funds_by_name(fund_name, insurer_name)
    matches = matched.get("ReturnValue", [])
    if not matches:
        return json.dumps({"error": f"No matching fund found for '{fund_name}'."})

    fund_id = matches[0].get("FundID")
    url = f"{INVESTMENT_API_BASE_URL}/enqapi/Quote/GetFundHoldingSectorBreakup"
    response = await make_get_request(url=url, params={"VRFundID": fund_id}, headers=_get_bot_headers())
    return json.dumps(response, default=str)


async def get_insurer_top_funds(insurer_name: str, top_n: int = 5) -> str:
    """Get top performing funds for a specific insurer."""
    logger.info(f"Getting top {top_n} funds for insurer: {insurer_name}")

    response = await get_all_funds_master()
    if "error" in response:
        return json.dumps(response)

    funds = response.get("ReturnValue", [])
    if not isinstance(funds, list):
        return json.dumps({"error": "Invalid funds data"})

    # Filter by insurer
    matching = [f for f in funds if isinstance(f, dict) and _insurer_matches(insurer_name, str(f.get("InsurerName", "")))]
    if not matching:
        return json.dumps({"error": f"No funds found for insurer '{insurer_name}'."})

    # Sort by 10Y return
    matching.sort(key=lambda f: f.get("Ret10YR") or 0, reverse=True)
    top = [{"FundName": f.get("FundName"), "5Y": f.get("FiveYrGrowth"), "7Y": f.get("Ret7YR"), "10Y": f.get("Ret10YR")} for f in matching[:top_n]]

    return json.dumps({"insurer": insurer_name, "total_funds": len(matching), "top_funds": top}, default=str)


async def get_plan_funds_split_by_type(plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
    """Get funds split into active/passive categories for a plan."""
    logger.info(f"Getting funds split by type for plan: {plan_name}")

    # Reuse plan fund performance to get all funds
    result = await get_plan_fund_performance(plan_name, insurer_name, top_n=50)
    data = json.loads(result)

    if "error" in data:
        return result

    # For now, return all as "active" since passive classification needs NFO timeline
    funds = data.get("top_funds", [])
    return json.dumps({
        "plan": data.get("plan"),
        "active_funds": funds[:top_n],
        "passive_funds": [],
        "note": "Passive fund classification will be available once NFO timeline is integrated."
    }, default=str)


async def compare_funds(fund_name_1: str, fund_name_2: str, insurer_name_1: Optional[str] = None, insurer_name_2: Optional[str] = None) -> str:
    """Compare two funds side by side."""
    logger.info(f"Comparing: {fund_name_1} vs {fund_name_2}")

    resp1 = await search_funds_by_name(fund_name_1, insurer_name_1)
    resp2 = await search_funds_by_name(fund_name_2, insurer_name_2)

    matches1 = resp1.get("ReturnValue", [])
    matches2 = resp2.get("ReturnValue", [])

    if not matches1:
        return json.dumps({"error": f"No matching fund found for '{fund_name_1}'"})
    if not matches2:
        return json.dumps({"error": f"No matching fund found for '{fund_name_2}'"})

    fund1 = _format_fund_details(matches1[0])
    fund2 = _format_fund_details(matches2[0])

    return json.dumps({"fund_1": fund1, "fund_2": fund2}, default=str)
