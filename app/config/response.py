from app.models.customer import CustomerProfileResponse


def create_success_response(unique_id: str) -> CustomerProfileResponse:
    return CustomerProfileResponse(unique_id=unique_id, isSuccess=True, errors=None)


def create_error_response(errors: list[str]) -> CustomerProfileResponse:
    return CustomerProfileResponse(unique_id="", isSuccess=False, errors=errors)
