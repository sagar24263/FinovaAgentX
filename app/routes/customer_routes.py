from fastapi import APIRouter

from app.config.onboarding_service import OnboardingService
from app.config.response import create_error_response, create_success_response
from app.models.customer import CustomerProfileRequest, CustomerProfileResponse
from app.utils.logger import get_logger

logger = get_logger("customer")

router = APIRouter()
onboarding_service = OnboardingService()


@router.post("/save-customer-profile", response_model=CustomerProfileResponse)
async def save_customer_profile(request: CustomerProfileRequest):
    logger.info(f"Saving customer profile ProductID={request.ProductID}, UserId={request.UserId!r}")

    try:
        unique_id = await onboarding_service.onboard_customer(request)
        return create_success_response(unique_id)
    except Exception as e:
        logger.error(f"Customer onboarding failed: {e}")
        return create_error_response([str(e)])
