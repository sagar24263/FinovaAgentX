from fastapi import APIRouter, HTTPException

from app.models.item import Item, ItemCreate

router = APIRouter()

# ============================================================================
# Items
# ============================================================================

# In-memory store for demo purposes
_items: dict[int, Item] = {}
_next_id: int = 1


@router.get("/items", response_model=list[Item], tags=["items"])
async def list_items():
    return list(_items.values())


@router.get("/items/{item_id}", response_model=Item, tags=["items"])
async def get_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    return _items[item_id]


@router.post("/items", response_model=Item, status_code=201, tags=["items"])
async def create_item(payload: ItemCreate):
    global _next_id
    item = Item(id=_next_id, **payload.model_dump())
    _items[_next_id] = item
    _next_id += 1
    return item


@router.delete("/items/{item_id}", status_code=204, tags=["items"])
async def delete_item(item_id: int):
    if item_id not in _items:
        raise HTTPException(status_code=404, detail="Item not found")
    del _items[item_id]
