from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="FastAPI App", version="0.1.0")

app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
