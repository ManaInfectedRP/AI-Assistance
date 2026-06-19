import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.chat import ChatRequest
from app.services.model_provider import stream_completion
from app.services.web_search import build_web_context, inject_context

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    messages = [m.model_dump() for m in req.messages]

    if req.web_search:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            None,
        )
        if last_user:
            context = await build_web_context(last_user)
            messages = inject_context(messages, context)

    async def sse_generator():
        async for delta in stream_completion(messages, settings.chat_model):
            chunk = json.dumps({"delta": delta, "done": False})
            yield f"data: {chunk}\n\n"
        yield f"data: {json.dumps({'delta': '', 'done': True})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
