from typing import Literal, Optional
from pydantic import BaseModel

KnowledgeBaseType = Literal["generic", "NFO"]


class ReindexRequest(BaseModel):
    type: Optional[KnowledgeBaseType] = None  # None means reindex both


class ReindexResponse(BaseModel):
    isSuccess: bool
