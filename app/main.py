from fastapi import FastAPI

from app.routes.customer_routes import router as customer_router

app = FastAPI(title="FastAPI App", version="0.1.0")

app.include_router(customer_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
