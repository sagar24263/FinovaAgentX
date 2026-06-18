from fastapi import APIRouter

from app.api.endpoints import customer, items

api_router = APIRouter()

api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(customer.router, tags=["customer"])
