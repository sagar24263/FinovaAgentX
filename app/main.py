from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

from app.routes.customer_routes import router as customer_router
from app.routes.chat_routes import router as chat_router

app = FastAPI(title="FastAPI App", version="0.1.0")
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(customer_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/chat", response_class=FileResponse)
async def chat():
    return os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
