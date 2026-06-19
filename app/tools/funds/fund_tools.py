from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.fund_service import (
    compare_funds,
    get_fund_asset_class_breakup,
    get_fund_details,
    get_fund_holding_sector_breakup,
    get_insurer_top_funds,
    get_plan_fund_performance,
    get_plan_funds_split_by_type,
)


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class GetFundDetailsInput(BaseModel):
    fund_name: str = Field(description="The name of the fund to look up, without insurer name")
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name if mentioned")


class GetPlanFundPerformanceInput(BaseModel):
    plan_name: str = Field(description="Plan product name for fund ranking (e.g. 'Signature', 'Click2Invest')")
    insurer_name: Optional[str] = Field(default=None, description="Insurer name if mentioned separately")
    top_n: Optional[int] = Field(default=5, description="Number of top funds to return (default 5)")


class GetFundBreakupInput(BaseModel):
    fund_name: str = Field(description="The fund name to get breakup for")
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name")


class GetInsurerTopFundsInput(BaseModel):
    insurer_name: str = Field(description="Insurer name (e.g. 'HDFC Life', 'ICICI Pru Life')")
    top_n: Optional[int] = Field(default=5, description="Number of top funds to return (default 5)")


class GetPlanFundsSplitByTypeInput(BaseModel):
    plan_name: str = Field(description="Plan name to get funds for")
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name")
    top_n: Optional[int] = Field(default=5, description="Number of top funds per category (default 5)")


class CompareFundsInput(BaseModel):
    fund_name_1: str = Field(description="First fund name to compare")
    fund_name_2: str = Field(description="Second fund name to compare")
    insurer_name_1: Optional[str] = Field(default=None, description="Optional insurer for first fund")
    insurer_name_2: Optional[str] = Field(default=None, description="Optional insurer for second fund")


# ---------------------------------------------------------------------------
# Tool Classes
# ---------------------------------------------------------------------------

class GetFundDetailsTool(BaseTool):
    name: str = "get_fund_details"
    description: str = (
        "Look up one fund by name. Returns fund returns (5Y/7Y/10Y) and mapped plans. "
        "Use when user asks about a specific fund's performance or details."
    )
    args_schema: Type[BaseModel] = GetFundDetailsInput

    async def _arun(self, fund_name: str, insurer_name: Optional[str] = None) -> str:
        return await get_fund_details(fund_name, insurer_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetPlanFundPerformanceTool(BaseTool):
    name: str = "get_plan_fund_performance"
    description: str = (
        "Ranked fund performance for a ULIP/plan sorted by 10-year return. "
        "Use for 'top N funds in [plan]', 'best funds in ICICI Signature'."
    )
    args_schema: Type[BaseModel] = GetPlanFundPerformanceInput

    async def _arun(self, plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
        return await get_plan_fund_performance(plan_name, insurer_name, top_n)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetFundAssetClassBreakupTool(BaseTool):
    name: str = "get_fund_asset_class_breakup"
    description: str = "Get breakup of a fund's investments across asset classes (equity, debt, etc)."
    args_schema: Type[BaseModel] = GetFundBreakupInput

    async def _arun(self, fund_name: str, insurer_name: Optional[str] = None) -> str:
        return await get_fund_asset_class_breakup(fund_name, insurer_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetFundHoldingSectorBreakupTool(BaseTool):
    name: str = "get_fund_holding_sector_breakup"
    description: str = "Get sector-wise holding breakup of a fund's investments."
    args_schema: Type[BaseModel] = GetFundBreakupInput

    async def _arun(self, fund_name: str, insurer_name: Optional[str] = None) -> str:
        return await get_fund_holding_sector_breakup(fund_name, insurer_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetInsurerTopFundsTool(BaseTool):
    name: str = "get_insurer_top_funds"
    description: str = (
        "Get the top performing funds for a specific insurer sorted by 10-year return. "
        "Use for 'top funds in Axis Max', 'best HDFC funds'."
    )
    args_schema: Type[BaseModel] = GetInsurerTopFundsInput

    async def _arun(self, insurer_name: str, top_n: int = 5) -> str:
        return await get_insurer_top_funds(insurer_name, top_n)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetPlanFundsSplitByTypeTool(BaseTool):
    name: str = "get_plan_funds_split_by_type"
    description: str = (
        "Get plan funds split into Active and Passive categories with top N of each. "
        "Preferred when user asks about funds in a plan."
    )
    args_schema: Type[BaseModel] = GetPlanFundsSplitByTypeInput

    async def _arun(self, plan_name: str, insurer_name: Optional[str] = None, top_n: int = 5) -> str:
        return await get_plan_funds_split_by_type(plan_name, insurer_name, top_n)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class CompareFundsTool(BaseTool):
    name: str = "compare_funds"
    description: str = (
        "Compare two funds side by side — returns, benchmark, NAV, and plans. "
        "Use for 'compare X fund vs Y fund'."
    )
    args_schema: Type[BaseModel] = CompareFundsInput

    async def _arun(self, fund_name_1: str, fund_name_2: str, insurer_name_1: Optional[str] = None, insurer_name_2: Optional[str] = None) -> str:
        return await compare_funds(fund_name_1, fund_name_2, insurer_name_1, insurer_name_2)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")
