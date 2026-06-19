import json
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from app.services.plan_service import get_insurer_info


class GetInsurerInfoInput(BaseModel):
    insurer_name: str = Field(description="The name of the insurer to get information for")


class GetInsurerInfoTool(BaseTool):
    name: str = "get_insurer_info"
    description: str = "Returns the insurer information"
    args_schema: Type[BaseModel] = GetInsurerInfoInput

    async def _arun(self, insurer_name: str) -> str:
        insurer_data = await get_insurer_info(insurer_name)
        return json.dumps(insurer_data, default=str)

    def _run(self, *args, **kwargs) -> str:
        raise NotImplementedError("This tool only supports async usage.")
