from pydantic import BaseModel


class ItemCreate(BaseModel):
    name: str
    description: str | None = None
    price: float


class Item(ItemCreate):
    id: int
