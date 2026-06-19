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
        "Get NFOs that are CURRENTLY OPEN for subscription right now. "
        "Use ONLY when user asks 'what NFOs are open/active/available right now'. "
        "Do NOT use for 'recent NFOs' or 'NFOs launched recently' — use get_nfo_timeline for that."
    )
    args_schema: Type[BaseModel] = GetActiveNfosInput

    async def _arun(self) -> str:
        return await get_active_nfos()

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")


class GetNfoTimelineTool(BaseTool):
    name: str = "get_nfo_timeline"
    description: str = (
        "Get NFO launch history — which funds were launched as NFOs and when. "
        "Use for 'recent NFOs', 'NFOs launched this year', 'what launched last month', "
        "'NFO history', 'timeline for HDFC NFOs'. Shows fund name, insurer, type, and listing returns."
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
        "Check which funds are CLOSED for subscription (no longer accepting investments). "
        "These are funds that were previously open (some launched as NFOs) but are now closed. "
        "Use for 'is X fund still open?', 'which funds are closed?', 'closed funds'."
    )
    args_schema: Type[BaseModel] = GetClosedFundsInput

    async def _arun(self, insurer_name: Optional[str] = None, fund_name: Optional[str] = None) -> str:
        return await get_closed_funds(insurer_name, fund_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")
