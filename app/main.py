from fastapi import FastAPI

from app.routes.customer_routes import router as customer_router
from app.routes.chat_routes import router as chat_router

app = FastAPI(title="FastAPI App", version="0.1.0")

app.include_router(customer_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
