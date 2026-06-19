"""
NFO Tools — LangChain tools for the NFO/Funds agent.
"""

from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.services.nfo_service import get_active_nfos


class GetActiveNfosInput(BaseModel):
    """No input required."""
    pass


class GetActiveNfosTool(BaseTool):
    name: str = "get_active_nfos"
    description: str = (
        "Get all currently active NFOs across product lanes: Growth/ULIP, Pension, and Gift. "
        "Use when the user asks about active NFOs, what's open, currently running NFOs, "
        "or 'what NFOs are available right now'. "
        "Returns insurer name and fund name for each active NFO."
    )
    args_schema: Type[BaseModel] = GetActiveNfosInput

    async def _arun(self) -> str:
        return await get_active_nfos()

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")
