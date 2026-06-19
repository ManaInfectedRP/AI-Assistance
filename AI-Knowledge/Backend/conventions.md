# Backend Conventions

## Structure
- Routers are thin: receive request, call service, return response. No logic inside routers.
- Business logic goes in `app/services/`
- Pydantic v2 models for all inputs and outputs — use `model_dump()` not `.dict()`
- `app/config.py` is the single source of truth for all settings (env vars)

## HTTP Client
- Always use `httpx.AsyncClient` for outbound requests — never `requests` (blocking)
- Timeout: 120s for model calls, 3s for health checks

## Provider Abstraction
- All model calls go through `stream_completion()` in `app/services/model_provider.py`
- Never call Ollama (or any other provider) directly from a router
- To add a new provider: implement `_stream_<provider>()` and add a branch in `stream_completion()`

## Testing
- Use `httpx.AsyncClient` with `ASGITransport` — no real server needed
- Patch `app.services.model_provider.stream_completion` in tests — never hit real Ollama
- Fixtures in `tests/conftest.py`
- Run: `pytest tests/ -v --cov=app`
