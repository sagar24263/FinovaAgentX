from fastapi import APIRouter

from app.routes.customer_routes import router as customer_router
from app.routes.item_routes import router as item_router

router = APIRouter()

router.include_router(item_router, prefix="/items", tags=["items"])
router.include_router(customer_router, tags=["customer"])
