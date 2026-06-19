from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routes.customer_routes import router as customer_router
from app.routes.chat_routes import router as chat_router
from app.routes.knowledge_base_routes import router as kb_router
from app.routes.pdf_parser_routes import router as pdf_parser_router
from app.services.knowledge_base_service import load_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_embedding_model()
    yield


app = FastAPI(title="FastAPI App", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

app.include_router(customer_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(kb_router, prefix="/api")
app.include_router(pdf_parser_router, prefix="/api")


@app.get("/chat", response_class=FileResponse)
async def chat():
    return os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
