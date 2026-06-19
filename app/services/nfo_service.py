"""
NFO Service — active NFOs, timeline, listing returns.
Reference: investmentagent/app/services/nfo_service.py
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL, NFO_TIMELINE_API_URL, NFO_TIMELINE_TIMEOUT
from app.utils.api_client import make_get_request, make_post_request
from app.utils.fuzzy_matcher import find_best_match
from app.utils.logger import get_logger

logger = get_logger("nfo_service")

ACTIVE_NFOS_URL = f"{INVESTMENT_API_BASE_URL}/bot/GetActiveNfos"


def _get_bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Active NFOs
# ---------------------------------------------------------------------------


async def get_active_nfos() -> str:
    """Fetch all currently active NFOs (Ml, Pension, Gift). Returns raw JSON."""
    logger.info(f"Calling active NFOs API: {ACTIVE_NFOS_URL}")

    try:
        response = await make_get_request(url=ACTIVE_NFOS_URL, headers=_get_bot_headers())

        if "error" in response:
            return json.dumps({"error": response["error"]})

        if response.get("HasError", True):
            return json.dumps({"error": "Failed to fetch active NFOs from the API."})

        return_value = response.get("ReturnValue", {})
        return json.dumps(return_value, default=str)

    except Exception as e:
        logger.error(f"Error getting active NFOs: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Timeline internals
# ---------------------------------------------------------------------------


def _rows_from_payload(data: Any) -> List[Dict[str, Any]]:
    """Extract rows from API response. API returns {"isSuccess": true, "data": [...]}."""
    if data is None:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        v = data.get("data")
        if isinstance(v, list):
            return [x for x in v if isinstance(x, dict)]
    return []


def _normalize_row(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Map API row to internal keys."""
    return {
        "nfo_month": (raw.get("nfoMonth") or "").strip(),
        "insurer_name": (raw.get("insurerName") or "").strip(),
        "fund_name": (raw.get("fundName") or "").strip(),
        "fund_type": (raw.get("fundType") or "").strip(),
        "insurer_id": raw.get("insurerID") or "",
        "listed_on_fund": (raw.get("listedOnFund") or "").strip(),
        "listing_basis": (raw.get("listingBasis") or "").strip(),
        "ret_1yr": (raw.get("ret1Yr") or "").strip(),
        "ret_3yr": (raw.get("ret3Yr") or "").strip(),
        "ret_5yr": (raw.get("ret5Yr") or "").strip(),
        "ret_7yr": (raw.get("ret7Yr") or "").strip(),
        "ret_10yr": (raw.get("ret10Yr") or "").strip(),
        "rsi": (raw.get("rsi") or "").strip(),
    }


async def _fetch_rows_from_api(
    insurer_id: Optional[int] = None,
    start_month: str = "January-2023",
    end_month: str = "December-2027",
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """POST to NFO timeline API. Returns (rows, error_token)."""
    url = (NFO_TIMELINE_API_URL or "").strip()
    if not url:
        return [], "not_configured"

    body: Dict[str, Any] = {"StartMonth": start_month, "EndMonth": end_month}
    if insurer_id is not None:
        body["InsurerID"] = insurer_id

    result = await make_post_request(url, json_data=body, headers=_get_bot_headers(), timeout=NFO_TIMELINE_TIMEOUT)

    if isinstance(result, dict) and result.get("error"):
        logger.error(f"NFO API error: {result.get('error')}")
        return [], "fetch_failed"

    if isinstance(result, dict) and result.get("isSuccess") is False:
        logger.error(f"NFO API isSuccess=false: {result.get('message')}")
        return [], "fetch_failed"

    rows_raw = _rows_from_payload(result)
    rows = [_normalize_row(r) for r in rows_raw]
    logger.info(f"NFO timeline: {len(rows)} rows, insurer_id={insurer_id}, window={start_month}..{end_month}")
    return rows, None


# ---------------------------------------------------------------------------
# Insurer name -> ID resolution
# ---------------------------------------------------------------------------


async def _resolve_insurer_id(insurer_name: str) -> Optional[int]:
    """Resolve insurer name to InsurerID using insurer master."""
    from app.services.plan_service import get_insurer_master

    try:
        response = await get_insurer_master()
        if "error" in response or response.get("HasError", True):
            return None

        insurers = response.get("ReturnValue", [])
        if not isinstance(insurers, list):
            return None

        result = find_best_match(
            query=insurer_name,
            candidates=insurers,
            get_name=lambda i: i.get("InsurerName", "") if isinstance(i, dict) else "",
            threshold=65.0,
        )

        if result:
            entry, score = result
            iid = entry.get("InsurerID") or entry.get("insurerID")
            if iid is not None:
                return int(iid)
        return None
    except Exception as e:
        logger.warning(f"Failed to resolve insurer_name={insurer_name}: {e}")
        return None


# ---------------------------------------------------------------------------
# get_nfo_timeline (tool)
# ---------------------------------------------------------------------------


async def get_nfo_timeline(
    insurer_name: Optional[str] = None,
    start_month: str = "January-2023",
    end_month: str = "December-2027",
) -> str:
    """Fetch NFO timeline rows for LLM consumption."""

    # Resolve insurer name to ID for better API filtering
    insurer_id = None
    if insurer_name:
        insurer_id = await _resolve_insurer_id(insurer_name)
        if insurer_id:
            logger.info(f"Resolved insurer '{insurer_name}' -> ID {insurer_id}")

    rows, err = await _fetch_rows_from_api(
        insurer_id=insurer_id,
        start_month=start_month,
        end_month=end_month,
    )

    if err == "not_configured":
        return "NFO timeline API is not configured (NFO_TIMELINE_API_URL)."
    if err == "fetch_failed":
        return "NFO timeline could not be loaded. Try again later."

    if not rows:
        return "No NFO timeline rows found for the given filters."

    # Format for LLM
    lines = [f"NFO timeline ({len(rows)} rows):", ""]
    for r in rows:
        returns_parts = []
        if r.get("listed_on_fund"):
            returns_parts.append(f"Listed on: {r['listed_on_fund']}")
        if r.get("listing_basis"):
            returns_parts.append(f"Basis: {r['listing_basis']}")
        for key, label in [("ret_1yr", "1Y"), ("ret_3yr", "3Y"), ("ret_5yr", "5Y"), ("ret_7yr", "7Y"), ("ret_10yr", "10Y")]:
            if r.get(key) and r[key] != "NA":
                returns_parts.append(f"{label}={r[key]}")
        if r.get("rsi") and r["rsi"] != "NA":
            returns_parts.append(f"RSI={r['rsi']}")
        returns_str = f" | {', '.join(returns_parts)}" if returns_parts else ""

        lines.append(
            f"- {r.get('nfo_month', '')} | {r.get('insurer_name', '')} | "
            f"{r.get('fund_name', '')} | {r.get('fund_type', '')}{returns_str}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# get_nfo_listing_returns (tool)
# ---------------------------------------------------------------------------


async def get_nfo_listing_returns(fund_name: str, insurer_name: Optional[str] = None) -> str:
    """Look up the returns at which a specific fund was listed as an NFO."""
    if not fund_name or not fund_name.strip():
        return "Fund name is required."

    rows, err = await _fetch_rows_from_api()

    if err:
        return f"Could not fetch NFO timeline: {err}"
    if not rows:
        return "No NFO timeline data available."

    # Fuzzy match
    result = find_best_match(
        query=fund_name.strip(),
        candidates=rows,
        get_name=lambda r: r.get("fund_name", ""),
        threshold=70.0,
        insurer_query=insurer_name,
        get_insurer=lambda r: r.get("insurer_name", ""),
    )

    if not result:
        suffix = f" from '{insurer_name}'" if insurer_name else ""
        return f"No NFO listing found for fund '{fund_name}'{suffix}."

    entry, score = result

    # Format
    parts = [
        f"**{entry.get('fund_name', '')}** by {entry.get('insurer_name', '')}",
        f"NFO Month: {entry.get('nfo_month')}",
        f"Fund Type: {entry.get('fund_type')}",
    ]

    if entry.get("listing_basis"):
        parts.append(f"Listing Basis: {entry['listing_basis']} returns")
    if entry.get("listed_on_fund"):
        parts.append(f"Listed on fund: {entry['listed_on_fund']}")

    returns_lines = []
    for key, label in [("ret_1yr", "1 Year"), ("ret_3yr", "3 Year"), ("ret_5yr", "5 Year"), ("ret_7yr", "7 Year"), ("ret_10yr", "10 Year")]:
        val = entry.get(key, "")
        if val and val != "NA":
            returns_lines.append(f"  - {label}: {val}")

    if returns_lines:
        parts.append("Returns at listing:")
        parts.extend(returns_lines)

    if entry.get("rsi") and entry["rsi"] != "NA":
        parts.append(f"RSI (Return Since Inception): {entry['rsi']}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# get_closed_funds (tool)
# ---------------------------------------------------------------------------


async def get_closed_funds(insurer_name: Optional[str] = None, fund_name: Optional[str] = None) -> str:
    """Check which NFO funds are closed for subscription."""
    logger.info(f"Getting closed funds: insurer={insurer_name}, fund={fund_name}")
    # TODO: Implement from closed_funds.json or API when available
    return json.dumps({"message": "Closed funds data not yet configured."})
