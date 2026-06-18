from pydantic import BaseModel, field_validator


class FaqRequest(BaseModel):
    query: str
    uniqueId: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must not be empty")
        return v.strip()

    @field_validator("uniqueId")
    @classmethod
    def unique_id_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("uniqueId must not be empty")
        return v.strip()


class FaqResponse(BaseModel):
    answer: str
    uniqueId: str
    isSuccess: bool
    errors: list[str] | None = None
