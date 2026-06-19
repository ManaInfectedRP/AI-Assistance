import httpx
from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "provider": settings.model_provider,
        "chat_model": settings.chat_model,
        "code_model": settings.code_model,
    }
