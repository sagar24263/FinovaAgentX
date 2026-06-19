from pydantic import BaseModel, field_validator

ALLOWED_USER_TYPES = {"Agent", "Customer", "Admin"}
ALLOWED_USER_SOURCES = {"Finova AgentX"}


class CustomerProfileRequest(BaseModel):
    UserId: str
    UserType: str
    UserSource: str
    ProductID: int

    @field_validator("UserId")
    @classmethod
    def user_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("UserId must not be empty")
        return v.strip()

    @field_validator("UserType")
    @classmethod
    def user_type_must_be_valid(cls, v: str) -> str:
        if v not in ALLOWED_USER_TYPES:
            raise ValueError(f"UserType must be one of {sorted(ALLOWED_USER_TYPES)}")
        return v

    @field_validator("UserSource")
    @classmethod
    def user_source_must_be_valid(cls, v: str) -> str:
        if v not in ALLOWED_USER_SOURCES:
            raise ValueError(f"UserSource must be one of {sorted(ALLOWED_USER_SOURCES)}")
        return v

    @field_validator("ProductID")
    @classmethod
    def product_id_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("ProductID must be a positive integer")
        return v


class MessageRecord(BaseModel):
    role: str
    content: str
    timestamp: str


class CustomerProfileResponse(BaseModel):
    unique_id: str
    isSuccess: bool
    errors: list[str] | None = None
    messages: list[MessageRecord] | None = None
