import json
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.calculation_service import (
    get_future_value_for_investment,
    get_required_investment_for_goal,
)


class GetRequiredInvestmentInput(BaseModel):
    goal_amount: int = Field(description="Required. The target amount you want to achieve (in rupees)")
    paying_year: Optional[int] = Field(
        default=10,
        description="(Optional) Years you will pay. Defaults to 10.",
    )
    total_tenure: Optional[int] = Field(
        default=20,
        description="(Optional) Total investment tenure in years. Defaults to 20.",
    )
    return_rate: Optional[float] = Field(
        default=15.0,
        description="(Optional) Expected annual return rate (%). Defaults to 15.",
    )
    frequency: Optional[int] = Field(
        default=12,
        description="(Optional) Payment frequency per year. Defaults to 12 (monthly).",
    )


class GetFutureValueInput(BaseModel):
    investment_amount: int = Field(description="Required. The amount you want to invest (in rupees)")
    paying_year: Optional[int] = Field(
        default=10,
        description="(Optional) Years you will pay. Defaults to 10.",
    )
    total_tenure: Optional[int] = Field(
        default=20,
        description="(Optional) Total investment tenure in years. Defaults to 20.",
    )
    return_rate: Optional[float] = Field(
        default=15.0,
        description="(Optional) Expected annual return rate (%). Defaults to 15.",
    )
    frequency: Optional[int] = Field(
        default=12,
        description="(Optional) Payment frequency per year. Defaults to 12 (monthly).",
    )


class GetRequiredInvestmentTool(BaseTool):
    name: str = "get_required_investment_for_goal"
    description: str = (
        "Use this function IMMEDIATELY when a user states a financial target or goal, "
        "such as 'I want to make 1 crore' or 'my goal is 50 lakhs'. "
        "It calculates the investment needed and is designed to be called with only the `goal_amount`, "
        "using intelligent defaults for other parameters."
    )
    args_schema: Type[BaseModel] = GetRequiredInvestmentInput

    async def _arun(
        self,
        goal_amount: int,
        paying_year: Optional[int] = 10,
        total_tenure: Optional[int] = 20,
        return_rate: Optional[float] = 15,
        frequency: Optional[int] = 12,
    ) -> str:
        result = await get_required_investment_for_goal(
            goal_amount=goal_amount,
            paying_year=paying_year,
            total_tenure=total_tenure,
            return_rate=return_rate,
            frequency=frequency,
        )
        return json.dumps(result, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")


class GetFutureValueTool(BaseTool):
    name: str = "get_future_value_for_investment"
    description: str = (
        "Use this function when a user asks about the potential growth of a regular investment, "
        "such as 'what will 5000 a month become' or 'how much will I have if I invest for 10 years'. "
        "It calculates the expected future corpus."
    )
    args_schema: Type[BaseModel] = GetFutureValueInput

    async def _arun(
        self,
        investment_amount: int,
        paying_year: Optional[int] = 10,
        total_tenure: Optional[int] = 20,
        return_rate: Optional[float] = 15,
        frequency: Optional[int] = 12,
    ) -> str:
        result = await get_future_value_for_investment(
            investment_amount=investment_amount,
            paying_year=paying_year,
            total_tenure=total_tenure,
            return_rate=return_rate,
            frequency=frequency,
        )
        return json.dumps(result, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")
