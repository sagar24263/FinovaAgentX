from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.insurer_service import get_insurer_info


class GetInsurerInfoInput(BaseModel):
    insurer_name: str = Field(description="The name of the insurer to get information for")


class GetInsurerInfoTool(BaseTool):
    name: str = "get_insurer_info"
    description: str = "Returns insurer information including available plans and company details."
    args_schema: Type[BaseModel] = GetInsurerInfoInput

    async def _arun(self, insurer_name: str) -> str:
        return await get_insurer_info(insurer_name)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("Async only.")
