# Backend Conventions

Stack: **Python 3.12**, **FastAPI 0.115**, **Pydantic v2.11**, **httpx 0.28**, **pytest 8 + pytest-asyncio 0.26**

---

## Project Structure

```
app/
├── main.py          # FastAPI app, middleware, router registration
├── config.py        # pydantic-settings Settings class — all env vars here
├── routers/         # Thin: receive → call service → return response
├── services/        # Business logic, external calls, model provider
└── schemas/         # Pydantic v2 request/response models
```

**Rule:** Routers contain zero business logic. Services contain zero HTTP routing.

---

## Python 3.12 Patterns

```python
# ✅ Built-in generics (no `from __future__ import annotations` needed)
def get_items(ids: list[int]) -> dict[str, list[str]]:
    ...

# ✅ Union shorthand
def process(value: str | int | None) -> str:
    ...

# ✅ type alias (3.12+)
type ModelName = str
type MessageList = list[dict[str, str]]

# ✅ match statement for dispatch
match settings.model_provider:
    case "ollama":
        ...
    case "openai":
        ...
    case _:
        raise ValueError(f"Unknown provider: {settings.model_provider}")

# ✅ asyncio.to_thread for sync code in async context
result = await asyncio.to_thread(sync_heavy_function, arg1, arg2)

# ✅ Exception groups (3.11+)
try:
    async with asyncio.TaskGroup() as tg:
        t1 = tg.create_task(fetch_a())
        t2 = tg.create_task(fetch_b())
except* ValueError as eg:
    for exc in eg.exceptions:
        logger.error(exc)
```

---

## Pydantic v2 — Models

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import ConfigDict

# ✅ v2 config via ConfigDict (not inner class Config)
class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    messages: list[ChatMessage]
    stream: bool = True
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    web_search: bool = False

# ✅ field_validator (v2 — replaces @validator)
class UserInput(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be blank")
        return v.strip()

# ✅ model_validator (v2 — replaces @root_validator)
class DateRange(BaseModel):
    start: date
    end: date

    @model_validator(mode="after")
    def check_order(self) -> "DateRange":
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self

# ✅ Serialisation — use model_dump(), NOT .dict() (deprecated)
req.model_dump()                        # dict
req.model_dump(exclude_none=True)       # drop None fields
req.model_dump(include={"messages"})    # only specific fields
req.model_dump_json()                   # JSON string

# ✅ Discriminated unions
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
```

---

## FastAPI 0.115 Patterns

```python
# ✅ Lifespan (replaces on_event startup/shutdown)
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    await startup_tasks()
    yield
    # shutdown
    await cleanup()

app = FastAPI(lifespan=lifespan)

# ✅ Dependency injection
from fastapi import Depends

async def get_db() -> AsyncGenerator[Session, None]:
    async with SessionLocal() as session:
        yield session

@router.get("/items")
async def list_items(db: Session = Depends(get_db)) -> list[Item]:
    ...

# ✅ Response model — validates and filters output
@router.get("/health", response_model=HealthResponse)
async def health() -> dict:
    return {"status": "ok", "ollama": True}

# ✅ HTTPException with detail
from fastapi import HTTPException

raise HTTPException(status_code=404, detail="Conversation not found")
raise HTTPException(status_code=422, detail={"field": "messages", "error": "empty"})

# ✅ Background tasks
from fastapi import BackgroundTasks

@router.post("/chat")
async def chat(req: ChatRequest, tasks: BackgroundTasks) -> StreamingResponse:
    tasks.add_task(log_request, req)
    ...

# ✅ StreamingResponse for SSE
async def sse_generator():
    async for delta in stream_completion(messages, model):
        yield f"data: {json.dumps({'delta': delta, 'done': False})}\n\n"
    yield f"data: {json.dumps({'delta': '', 'done': True})}\n\n"

return StreamingResponse(
    sse_generator(),
    media_type="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
)

# ✅ Annotated for reusable deps
from typing import Annotated
DbDep = Annotated[Session, Depends(get_db)]

@router.get("/items")
async def list_items(db: DbDep) -> list[Item]:
    ...
```

---

## httpx — Async HTTP

```python
import httpx

# ✅ Timeout object — different values per operation type
timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=5.0)

# ✅ Streaming response
async with httpx.AsyncClient(timeout=timeout) as client:
    async with client.stream("POST", url, json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if line:
                chunk = json.loads(line)
                yield chunk.get("content", "")

# ✅ Parallel requests
async with httpx.AsyncClient() as client:
    a, b = await asyncio.gather(
        client.get("/api/a"),
        client.get("/api/b"),
    )

# ✅ Retry with backoff (manual)
for attempt in range(3):
    try:
        resp = await client.get(url)
        break
    except httpx.TransportError:
        if attempt == 2:
            raise
        await asyncio.sleep(2 ** attempt)
```

---

## Testing — pytest-asyncio 0.26

```python
# pytest.ini
# asyncio_mode = auto              ← all async tests run automatically
# asyncio_default_fixture_loop_scope = function

# conftest.py
from httpx import ASGITransport, AsyncClient
from app.main import app

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# ✅ Patch the router-level import, not the service module
@pytest.fixture
def mock_stream():
    async def fake(messages, model_name):
        for word in ["Hello", " world"]:
            yield word

    with patch("app.routers.chat.stream_completion", new=fake):
        with patch("app.routers.code.stream_completion", new=fake):
            yield

# ✅ Test async endpoints — no @pytest.mark.anyio needed with asyncio_mode=auto
async def test_chat_streams(client, mock_stream):
    async with client.stream("POST", "/api/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "stream": True,
    }) as r:
        assert r.status_code == 200
        lines = [l async for l in r.aiter_lines() if l.startswith("data:")]
    assert len(lines) >= 1
```

---

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# Use module-level logger — never print() in production code
logger.debug("Scraping %s", url)
logger.warning("DDG search failed: %s", exc)
logger.error("Unhandled exception", exc_info=True)
```

---

## Error Handling

```python
# ✅ Specific exceptions first, broad last
try:
    resp = await client.get(url, timeout=5.0)
    resp.raise_for_status()
except httpx.TimeoutException:
    logger.warning("Timeout fetching %s", url)
    return ""
except httpx.HTTPStatusError as e:
    logger.warning("HTTP %s for %s", e.response.status_code, url)
    return ""
except Exception:
    logger.exception("Unexpected error")
    return ""
```
