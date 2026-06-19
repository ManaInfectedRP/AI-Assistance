# API Contract — Frontend ↔ Backend

Base URL (dev): `http://localhost:8000` (proxied via Vite as `/api`)

---

## POST /api/chat

Routes to `qwen3` (general chat model).

**Request:**
```json
{
  "messages": [
    { "role": "user", "content": "Hello" }
  ],
  "stream": true,
  "temperature": 0.7
}
```

**Response:** `text/event-stream`
```
data: {"delta": "Hi", "done": false}
data: {"delta": " there!", "done": false}
data: {"delta": "", "done": true}
```

---

## POST /api/code

Routes to `qwen3-coder` (coding model). Identical schema to `/api/chat`.

---

## GET /api/health

**Response:**
```json
{
  "status": "ok",
  "ollama": true,
  "provider": "ollama",
  "chat_model": "qwen3",
  "code_model": "qwen3-coder"
}
```

---

## SSE Parsing (frontend)

```typescript
// Split stream on "\n\n", strip "data: " prefix, JSON.parse remainder
// Stop on chunk.done === true
```

The frontend uses `fetch` + `ReadableStream` (not `EventSource`) because EventSource
does not support POST requests.
