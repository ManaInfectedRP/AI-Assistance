# Architecture Decision Records

## ADR-001: SSE over WebSockets for streaming

**Decision:** Use Server-Sent Events (SSE) via `fetch` + `ReadableStream`, not WebSockets.

**Reason:** Streaming is strictly server-to-client (model output). SSE is simpler — no handshake, no bidirectional state, works through HTTP/2. `EventSource` is not used because it's GET-only; `fetch` with `ReadableStream` gives us full SSE over POST.

## ADR-002: Ollama over direct GGUF model loading

**Decision:** Ollama manages models; the backend proxies to its REST API.

**Reason:** Ollama handles process lifecycle, VRAM management, model hot-swapping, and quantization. Direct GGUF loading (llama-cpp-python) would require the backend to own GPU memory, making model switching complex.

## ADR-003: Provider abstraction in model_provider.py

**Decision:** All model calls route through a single `stream_completion()` async generator.

**Reason:** Switching from Ollama to OpenAI/Anthropic/OpenRouter is a one-line `.env` change with zero router code changes. The router never knows which provider is active.

## ADR-004: Vite dev proxy instead of CORS headers

**Decision:** Frontend dev server proxies `/api/*` to `localhost:8000` via Vite's `server.proxy`.

**Reason:** Eliminates preflight CORS requests during development. In production, a reverse proxy (nginx/Caddy) does the same thing, making CORS headers on the backend a true last-resort safety net rather than the primary mechanism.

## Future: OpenHands Agent Layer

When Docker Desktop is available:
1. `docker pull ghcr.io/all-hands-ai/openhands:main`
2. Add `backend/app/routers/agent.py` with `POST /api/agent/run`
3. That router calls OpenHands' API with task payloads
4. Frontend gets a third `ModelMode`: `"agent"`
