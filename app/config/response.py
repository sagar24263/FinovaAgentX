from typing import Optional
from app.models.customer import CustomerProfileResponse, MessageRecord


def create_success_response(
    unique_id: str,
    messages: Optional[list[MessageRecord]] = None,
) -> CustomerProfileResponse:
    return CustomerProfileResponse(unique_id=unique_id, isSuccess=True, errors=None, messages=messages)


def create_error_response(errors: list[str]) -> CustomerProfileResponse:
    return CustomerProfileResponse(unique_id="", isSuccess=False, errors=errors)
