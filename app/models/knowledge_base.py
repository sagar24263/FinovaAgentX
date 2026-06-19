from typing import Literal, Optional
from pydantic import BaseModel

KnowledgeBaseType = Literal["generic", "NFO"]


class ReindexRequest(BaseModel):
    type: Optional[KnowledgeBaseType] = None  # None means reindex both


class CollectionStats(BaseModel):
    type: str
    mongo_collection: str
    qdrant_collection: str
    docs_indexed: int
    time_taken_seconds: float


class ReindexResponse(BaseModel):
    isSuccess: bool
    total_docs_indexed: int
    total_time_seconds: float
    collections: list[CollectionStats]
    errors: list[str] | None = None
