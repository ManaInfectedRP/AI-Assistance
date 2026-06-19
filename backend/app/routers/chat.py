import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.chat import ChatRequest
from app.services.model_provider import stream_completion

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(req: ChatRequest) -> StreamingResponse:
    messages = [m.model_dump() for m in req.messages]

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
