import json
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.plan_service import (
    compare_plans,
    get_plan_details,
    get_plans_by_insurer,
    get_top_plans,
)
from app.utils.data_formatter import format_top_plans_response


class ComparePlansInput(BaseModel):
    planName1: str = Field(description="The name of the first plan to compare")
    planName2: str = Field(description="The name of the second plan to compare")
    insurerName1: Optional[str] = Field(
        default=None,
        description="Optional: The insurer for the first plan. Only use this if the user provides it. Do not ask for it.",
    )
    insurerName2: Optional[str] = Field(
        default=None,
        description="Optional: The insurer for the second plan. Only use this if the user provides it. Do not ask for it.",
    )


class GetPlanDetailsInput(BaseModel):
    planName: str = Field(description="The name of the plan to get details for (without insurer name)")
    insurer_name: Optional[str] = Field(
        default=None,
        description="Optional: The insurer name if mentioned by user. Extract this separately from plan name.",
    )


class GetTopPlansInput(BaseModel):
    count: Optional[int] = Field(5, description="(Optional) Number of top plans to retrieve. Defaults to 5.")


class GetPlansByInsurerInput(BaseModel):
    insurer_name: str = Field(description="The name of the insurer to get plans for")
    count: Optional[int] = Field(3, description="(Optional) Number of plans to retrieve. Defaults to 3.")


class ComparePlansTool(BaseTool):
    name: str = "compare_plans"
    description: str = "Compare two plans and return the details of the plans its features, benefits, and returns data"
    args_schema: Type[BaseModel] = ComparePlansInput

    async def _arun(
        self,
        planName1: str,
        planName2: str,
        insurerName1: Optional[str] = None,
        insurerName2: Optional[str] = None,
    ) -> str:
        plans_data = await compare_plans(planName1, planName2, insurerName1, insurerName2)
        return json.dumps(plans_data, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")


class GetPlanDetailsTool(BaseTool):
    name: str = "get_plan_details"
    description: str = (
        "Returns the details of a particular plan including features, benefits, and returns data. "
        "If user mentions an insurer name extract it separately as insurer_name parameter."
    )
    args_schema: Type[BaseModel] = GetPlanDetailsInput

    async def _arun(self, planName: str, insurer_name: Optional[str] = None) -> str:
        plans_data = await get_plan_details(planName, insurer_name)
        return json.dumps(plans_data, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")


class GetTopPlansTool(BaseTool):
    name: str = "get_top_plans"
    description: str = """Returns top investment plans categorized by product type.
    Response contains ALL three categories:
    - capital_guarantee_plans: CG plans with capital protection
    - market_linked_plans: ULIP/ML plans with market-linked returns
    - high_sum_assured_plans: HSA plans with high life cover

    ALWAYS use this tool when user asks for top investment plans."""
    args_schema: Type[BaseModel] = GetTopPlansInput

    async def _arun(self, count: Optional[int] = 5) -> str:
        plans_data = await get_top_plans()
        formatted = format_top_plans_response(plans_data)
        return json.dumps(formatted, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")


class GetPlansByInsurerTool(BaseTool):
    name: str = "get_plans_by_insurer"
    description: str = (
        "Returns the top investment plan names from a specific insurer (default: 3 plans). "
        "Use this when user asks about plans from a specific company."
    )
    args_schema: Type[BaseModel] = GetPlansByInsurerInput

    async def _arun(self, insurer_name: str, count: Optional[int] = 3) -> str:
        plans_data = await get_plans_by_insurer(insurer_name, count)
        return json.dumps(plans_data, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")
