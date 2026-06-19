from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.models.knowledge_base import ReindexRequest, ReindexResponse
from app.services.knowledge_base_service import index_knowledge_base
from app.utils.logger import get_logger

logger = get_logger("knowledge_base_routes")

router = APIRouter()


@router.post("/reindex", response_model=ReindexResponse)
async def reindex(request: ReindexRequest):
    logger.info(f"Reindex request type={request.type!r}")
    try:
        result = await run_in_threadpool(index_knowledge_base, request.type)
        return ReindexResponse(isSuccess=len(result["errors"]) == 0)
    except Exception as e:
        logger.error(f"Reindex failed: {e}")
        return ReindexResponse(isSuccess=False)
