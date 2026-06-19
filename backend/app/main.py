from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import chat, code, health, knowledge

app = FastAPI(title="AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router,     prefix="/api")
app.include_router(chat.router,       prefix="/api")
app.include_router(code.router,       prefix="/api")
app.include_router(knowledge.router,  prefix="/api")
