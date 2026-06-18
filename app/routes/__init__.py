from fastapi import APIRouter

from app.routes.customer_routes import router as customer_router

router = APIRouter()

router.include_router(customer_router, tags=["customer"])
