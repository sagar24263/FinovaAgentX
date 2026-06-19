from typing import Any, Dict

from app.config.env import INVESTMENT_API_BASE_URL
from app.utils.api_client import make_get_request
from app.utils.logger import get_logger

_logger = get_logger("calculation_service")

ENDPOINTS = {
    "power_of_compounding": f"{INVESTMENT_API_BASE_URL}/enqapi/Quote/PowerOfCompoundingCalculator"
}


async def get_required_investment_for_goal(
    goal_amount: int,
    paying_year: int = 10,
    total_tenure: int = 20,
    return_rate: float = 15,
    frequency: int = 12,
) -> Dict[str, Any]:
    if not goal_amount or goal_amount <= 0:
        return {"error": "Goal amount is required and must be greater than 0"}

    _logger.info(f"Calculating required investment for goal: ₹{goal_amount:,}")

    params = {
        "goalAmount": goal_amount,
        "payingYear": paying_year,
        "totalTenure": total_tenure,
        "returnRate": return_rate,
        "frequency": frequency,
    }

    return await make_get_request(
        url=ENDPOINTS["power_of_compounding"],
        params=params,
    )


async def get_future_value_for_investment(
    investment_amount: int,
    paying_year: int = 10,
    total_tenure: int = 20,
    return_rate: float = 15,
    frequency: int = 12,
) -> Dict[str, Any]:
    if not investment_amount or investment_amount <= 0:
        return {"error": "Investment amount is required and must be greater than 0"}

    _logger.info(f"Calculating future value for investment: ₹{investment_amount:,}")

    params = {
        "investmentAmount": investment_amount,
        "payingYear": paying_year,
        "totalTenure": total_tenure,
        "returnRate": return_rate,
        "frequency": frequency,
    }

    return await make_get_request(
        url=ENDPOINTS["power_of_compounding"],
        params=params,
    )
