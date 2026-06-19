"""
doc_context.py — reads AI-Knowledge markdown files from local project repos
and builds a context string that can be injected into the system message.
"""
import asyncio
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


async def get_available_projects() -> list[dict]:
    """Scan PROJECTS_ROOT for directories that contain an AI-Knowledge folder."""

    def _scan() -> list[dict]:
        root = Path(settings.projects_root)
        if not root.exists():
            logger.warning("projects_root does not exist: %s", root)
            return []

        projects = []
        for proj_dir in sorted(root.iterdir()):
            if not proj_dir.is_dir():
                continue
            knowledge_dir = proj_dir / "AI-Knowledge"
            if not knowledge_dir.exists():
                continue
            docs = list(knowledge_dir.rglob("*.md"))
            if not docs:
                continue
            projects.append(
                {
                    "id": proj_dir.name,
                    "name": proj_dir.name,
                    "doc_count": len(docs),
                }
            )
        return projects

    return await asyncio.to_thread(_scan)


async def build_doc_context(project_id: str) -> str:
    """
    Read all *.md files under {PROJECTS_ROOT}/{project_id}/AI-Knowledge/
    and return a single formatted context string ready to inject as a
    system message.
    """

    def _read() -> str:
        root = Path(settings.projects_root)
        knowledge_dir = root / project_id / "AI-Knowledge"
        if not knowledge_dir.exists():
            logger.warning("AI-Knowledge not found for project: %s", project_id)
            return ""

        parts: list[str] = []
        for md_file in sorted(knowledge_dir.rglob("*.md")):
            try:
                content = md_file.read_text(encoding="utf-8")
                rel = md_file.relative_to(knowledge_dir)
                parts.append(f"### {rel}\n\n{content.strip()}")
            except Exception:
                logger.warning("Could not read %s", md_file, exc_info=True)

        if not parts:
            return ""

        header = (
            f"# Project Knowledge: {project_id}\n\n"
            f"The following documentation describes the {project_id} project's "
            f"conventions, patterns, and architecture. Use it as authoritative "
            f"reference when answering questions about this project.\n\n"
        )
        return header + "\n\n---\n\n".join(parts)

    return await asyncio.to_thread(_read)
