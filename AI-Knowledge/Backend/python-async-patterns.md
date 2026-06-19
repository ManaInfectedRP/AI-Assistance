# Python Async Patterns — FastAPI / httpx / asyncio

Stack: **Python 3.12**, **asyncio**, **httpx 0.28**, **FastAPI 0.115**

---

## Core asyncio rules

```python
# ✅ async def + await — always pair them
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text

# ✅ asyncio.gather — run independent coroutines concurrently
async def fetch_all(urls: list[str]) -> list[str]:
    results = await asyncio.gather(*[fetch_data(u) for u in urls])
    return list(results)

# ✅ asyncio.to_thread — run blocking/sync code without blocking event loop
import asyncio

def _sync_search(query: str) -> list[dict]:
    # duckduckgo-search is sync — must not be called directly in async
    from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=5))

async def search(query: str) -> list[dict]:
    return await asyncio.to_thread(_sync_search, query)
```

---

## AsyncGenerator — streaming / SSE

```python
from typing import AsyncGenerator

# ✅ Yields values incrementally — used for SSE StreamingResponse
async def stream_completion(
    messages: list[dict],
    model_name: str,
) -> AsyncGenerator[str, None]:
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if delta := chunk.get("message", {}).get("content", ""):
                    yield delta   # ← each yield sends one SSE event
                if chunk.get("done"):
                    break

# ✅ Consuming an AsyncGenerator in a FastAPI route
async def sse_generator():
    async for delta in stream_completion(messages, model):
        data = json.dumps({"delta": delta, "done": False})
        yield f"data: {data}\n\n"
    yield f"data: {json.dumps({'delta': '', 'done': True})}\n\n"

return StreamingResponse(sse_generator(), media_type="text/event-stream")
```

---

## asyncio.TaskGroup (3.11+) — structured concurrency

```python
async def fetch_pages(urls: list[str]) -> list[str]:
    results: list[str] = []
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch_data(u)) for u in urls]
        # All tasks finished here — no exceptions leaked
        results = [t.result() for t in tasks]
    except* httpx.TimeoutException as eg:
        # Exception group — handle per-task failures
        logger.warning("Some pages timed out: %d errors", len(eg.exceptions))
    return results

# ✅ For simple parallel awaits without error grouping — asyncio.gather is simpler:
a, b, c = await asyncio.gather(fetch_data(url1), fetch_data(url2), fetch_data(url3))
```

---

## httpx — timeout tuning

```python
import httpx

# ✅ Different timeout for each phase — critical for LLM streaming
timeout = httpx.Timeout(
    connect=10.0,   # time to open TCP connection
    read=None,      # None = no limit — LLMs can take minutes to start
    write=30.0,     # time to finish sending request body
    pool=5.0,       # time to acquire connection from pool
)

# ❌ This causes ReadTimeout when model takes >120s to respond:
# async with httpx.AsyncClient(timeout=120.0) as client: ...

# ✅ Single scalar timeout only if ALL phases can be the same
async with httpx.AsyncClient(timeout=5.0) as client:
    resp = await client.get("/api/health")
```

---

## Context managers — async with

```python
# ✅ AsyncClient as context manager — auto-closes connection pool
async with httpx.AsyncClient() as client:
    resp = await client.get(url)

# ✅ Multiple resources — nested or parenthesised
async with (
    httpx.AsyncClient() as client,
    aiofiles.open("log.txt", "a") as f,
):
    ...

# ✅ Writing your own async context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_connection(dsn: str):
    conn = await connect(dsn)
    try:
        yield conn
    finally:
        await conn.close()

async with managed_connection("postgres://...") as conn:
    rows = await conn.fetch("SELECT 1")
```

---

## Error handling — async style

```python
# ✅ Specific httpx errors first, broad last
async def safe_get(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text
    except httpx.TimeoutException:
        logger.warning("Timeout: %s", url)
        return ""
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP %d: %s", e.response.status_code, url)
        return ""
    except httpx.TransportError as e:
        logger.warning("Transport error: %s — %s", url, e)
        return ""
    except Exception:
        logger.exception("Unexpected error fetching %s", url)
        return ""

# ✅ asyncio.gather with return_exceptions=True — collect failures without stopping
results = await asyncio.gather(
    fetch_data(url1),
    fetch_data(url2),
    return_exceptions=True,   # exceptions become values in result list
)
for r in results:
    if isinstance(r, Exception):
        logger.warning("One request failed: %s", r)
    else:
        process(r)
```

---

## AbortSignal / cancellation

```python
# ✅ asyncio.CancelledError — handle cleanup on task cancellation
async def long_stream():
    try:
        async for chunk in llm_stream():
            yield chunk
    except asyncio.CancelledError:
        logger.info("Stream cancelled by client")
        raise   # always re-raise CancelledError

# ✅ asyncio.timeout (3.11+) — cancel after deadline
async with asyncio.timeout(30.0):
    result = await slow_operation()   # raises TimeoutError if >30s
```

---

## Pattern: inject web context before LLM call

This is the web search RAG pattern used in `services/web_search.py`:

```python
async def build_web_context(query: str, max_results: int = 5, scrape_top: int = 3) -> str:
    # 1. Sync DDG search → run in thread so it doesn't block event loop
    results = await asyncio.to_thread(_ddg_search, query, max_results)

    # 2. Scrape top pages concurrently
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5.0, read=8.0)) as client:
        scraped = await asyncio.gather(
            *[_scrape(r["href"], client) for r in results[:scrape_top]],
            return_exceptions=True,
        )

    # 3. Build formatted context string
    parts = []
    for result, content in zip(results, scraped):
        if isinstance(content, Exception):
            continue
        parts.append(f"### {result['title']}\nURL: {result['href']}\n{content[:1500]}")
    return "\n\n---\n\n".join(parts)

def inject_context(messages: list[dict], context: str) -> list[dict]:
    """Merge web context into existing system message, or prepend as new one."""
    if messages and messages[0].get("role") == "system":
        merged = messages[0]["content"] + "\n\n" + context
        return [{"role": "system", "content": merged}] + messages[1:]
    return [{"role": "system", "content": context}] + messages
```

---

## FastAPI lifespan — startup/shutdown async tasks

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — runs once before first request
    logger.info("Starting up…")
    await warmup_connection_pool()
    yield
    # Shutdown — runs after last request
    await connection_pool.close()
    logger.info("Shut down cleanly")

app = FastAPI(lifespan=lifespan)
```

---

## Common pitfalls

| Mistake | Fix |
|---|---|
| `await sync_function()` | Sync functions aren't awaitable — just call them directly, or wrap with `asyncio.to_thread()` if blocking |
| Calling `asyncio.run()` inside async code | Use `await` instead — `asyncio.run()` creates a new event loop |
| `timeout=120.0` for streaming LLM | Use `httpx.Timeout(read=None)` — scalar timeout applies to read phase too |
| Forgetting `async for` on async generator | `for` on async generator silently yields nothing |
| `asyncio.gather()` without `return_exceptions` | One failure cancels all others — add `return_exceptions=True` for parallel scraping |
| Opening `AsyncClient` per request in a loop | Create once, reuse — connection pool reuse matters for performance |
