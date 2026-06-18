from fastapi import APIRouter
from pydantic import BaseModel

from app.config.redis import get_redis_client
from app.config.response import create_error_response, create_success_response
from app.models.customer import CustomerProfileRequest, CustomerProfileResponse
from app.services.onboarding_service import OnboardingService
from app.utils.logger import get_logger

logger = get_logger("customer")

router = APIRouter()
onboarding_service = OnboardingService()


class ResetChatRequest(BaseModel):
    UserId: str
    ProductID: int


@router.post("/save-customer-profile", response_model=CustomerProfileResponse)
async def save_customer_profile(request: CustomerProfileRequest):
    logger.info(f"Saving customer profile ProductID={request.ProductID}, UserId={request.UserId!r}")

    try:
        unique_id = await onboarding_service.onboard_customer(request)
        return create_success_response(unique_id)
    except Exception as e:
        logger.error(f"Customer onboarding failed: {e}")
        return create_error_response([str(e)])


@router.post("/reset-chat", response_model=CustomerProfileResponse)
async def reset_chat(request: ResetChatRequest):
    logger.info(f"Resetting chat for UserId={request.UserId!r}, ProductID={request.ProductID}")

    try:
        redis_client = get_redis_client()
        if redis_client:
            redis_key = f"{onboarding_service.profile_prefix}{request.UserId}:{request.ProductID}"
            redis_client.delete(redis_key)
            logger.info(f"Redis key deleted: {redis_key}")

        return create_success_response("")
    except Exception as e:
        logger.error(f"Reset chat failed: {e}")
        return create_error_response([str(e)])
