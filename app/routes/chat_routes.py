from fastapi import APIRouter

from app.models.chat import FaqRequest, FaqResponse
from app.services.chat_service import ChatService
from app.utils.logger import get_logger

logger = get_logger("chat_routes")

router = APIRouter()
chat_service = ChatService()


@router.post("/get-faq-response", response_model=FaqResponse)
async def get_faq_response(request: FaqRequest):
    logger.info(f"FAQ request received for uniqueId={request.uniqueId}")

    try:
        answer = await chat_service.get_faq_response(request.query, request.uniqueId)
        return FaqResponse(
            answer=answer,
            uniqueId=request.uniqueId,
            isSuccess=True,
        )
    except Exception as e:
        logger.error(f"FAQ response failed: {e}")
        return FaqResponse(
            answer="",
            uniqueId=request.uniqueId,
            isSuccess=False,
            errors=[str(e)],
        )
