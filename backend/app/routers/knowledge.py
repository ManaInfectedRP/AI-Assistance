from fastapi import APIRouter

from app.services.doc_context import get_available_projects

router = APIRouter()


@router.get("/knowledge/projects")
async def list_projects() -> list[dict]:
    """Return all local repos that have an AI-Knowledge directory."""
    return await get_available_projects()
