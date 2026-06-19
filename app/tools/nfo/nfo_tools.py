from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.nfo_service import get_active_nfos, get_nfo_timeline, get_nfo_listing_returns, get_closed_funds


# ---------------------------------------------------------------------------
# Input Models
# ---------------------------------------------------------------------------

class GetActiveNfosInput(BaseModel):
    """No input required."""
    pass


class NfoTimelineInput(BaseModel):
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name filter (e.g. 'HDFC Life')")
    start_month: str = Field(default="January-2023", description="Range start in MonthName-YYYY format")
    end_month: str = Field(default="December-2027", description="Range end in MonthName-YYYY format")


class NfoListingReturnsInput(BaseModel):
    fund_name: str = Field(description="The NFO fund name to look up listing returns for")
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name for better matching")


class GetClosedFundsInput(BaseModel):
    insurer_name: Optional[str] = Field(default=None, description="Optional insurer name to filter")
    fund_name: Optional[str] = Field(default=None, description="Optional fund name to check if closed")


# ---------------------------------------------------------------------------
# Tool Classes
# ---------------------------------------------------------------------------

class GetActiveNfosTool(BaseTool):
    name: str = "get_active_nfos"
    description: str = (
        "Get all currently active NFOs across product lanes: Growth/ULIP, Pension, and Gift. "
        "Use when user asks about active/open/running NFOs."
    )
    args_schema: Type[BaseModel] = GetActiveNfosInput

    async def _arun(self) -> str:
        return await get_active_nfos()

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetNfoTimelineTool(BaseTool):
    name: str = "get_nfo_timeline"
    description: str = (
        "NFO launch-month timeline. Shows which funds were launched as NFOs, their listing returns. "
        "Use for 'NFO history', 'what launched in April 2025', 'NFO timeline for HDFC'."
    )
    args_schema: Type[BaseModel] = NfoTimelineInput

    async def _arun(self, insurer_name: Optional[str] = None, start_month: str = "January-2023", end_month: str = "December-2027") -> str:
        return await get_nfo_timeline(insurer_name, start_month, end_month)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetNfoListingReturnsTool(BaseTool):
    name: str = "get_nfo_listing_returns"
    description: str = (
        "Look up the returns at which a fund was listed as an NFO. "
        "Use for 'at what returns was X fund listed?', 'listing basis of X'."
    )
    args_schema: Type[BaseModel] = NfoListingReturnsInput

    async def _arun(self, fund_name: str, insurer_name: Optional[str] = None) -> str:
        return await get_nfo_listing_returns(fund_name, insurer_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetClosedFundsTool(BaseTool):
    name: str = "get_closed_funds"
    description: str = (
        "Check which NFO funds are closed for subscription. "
        "Use for 'is X fund still open?', 'which funds are closed?'."
    )
    args_schema: Type[BaseModel] = GetClosedFundsInput

    async def _arun(self, insurer_name: Optional[str] = None, fund_name: Optional[str] = None) -> str:
        return await get_closed_funds(insurer_name, fund_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")
