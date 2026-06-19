# AIAssistance

Local-first AI assistant for general chat and coding assistance. Runs entirely on your machine via Ollama — no cloud required for daily use. Cloud providers (OpenAI, Anthropic, OpenRouter) are available as optional upgrades via a single `.env` change.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 19 + TypeScript, Vite, SSE streaming |
| Backend | Python FastAPI, Pydantic v2, httpx |
| Models | `qwen3` (chat), `qwen3-coder` (code) via Ollama |
| VS Code | Continue extension — inline AI, tab autocomplete |
| Testing | Vitest + Playwright (frontend), Pytest (backend) |

## Quick Start

### Prerequisites
- [Ollama](https://ollama.com/download) installed and running (`ollama serve`)
- Node.js 18+ and Python 3.11+

### 1. Pull models
```bash
ollama pull qwen3
ollama pull qwen3-coder
```

### 2. Backend
```bash
cd backend
py -3.12 -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### Shortcut — start both at once
```bash
bash fastboot.sh
```

## Structure

```
AIAssistance/
├── fastboot.sh           Start backend + frontend together
├── backend/              FastAPI + Ollama proxy
│   ├── app/
│   │   ├── routers/      chat.py, code.py, health.py
│   │   ├── services/     model_provider.py (provider abstraction)
│   │   └── schemas/      Pydantic request/response models
│   └── tests/            Pytest suite (no Ollama required)
├── frontend/             React + TypeScript chat UI
│   ├── src/
│   │   ├── components/   ChatWindow, MessageBubble, InputBar, Sidebar
│   │   ├── hooks/        useChat (streaming), useConversations (localStorage)
│   │   └── api/          SSE client
│   └── e2e/              Playwright end-to-end tests
├── AI-Knowledge/         Project docs — load into Continue with @docs
│   ├── Frontend/         TypeScript + React conventions
│   ├── Backend/          FastAPI + testing conventions
│   ├── Architecture/     Decision records (ADRs)
│   └── Documentation/    API contract
└── .continue/            VS Code Continue extension config
```

## API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/chat` | Stream response from `qwen3` |
| POST | `/api/code` | Stream response from `qwen3-coder` |
| GET | `/api/health` | Health check + Ollama status |

All streaming responses use SSE (`text/event-stream`). Each chunk: `{"delta": "...", "done": false}`.

## Cloud Upgrade Path

Switch from local Ollama to a cloud provider with two steps:

1. Set `MODEL_PROVIDER` in `backend/.env`:

```env
MODEL_PROVIDER=openai        # or anthropic / openrouter
OPENAI_API_KEY=sk-...
```

2. Implement the matching stub in `backend/app/services/model_provider.py` — the routers and frontend require no changes.

## Running Tests

**Backend** (no Ollama required — model calls are mocked):
```bash
cd backend
venv\Scripts\activate
pytest tests/ -v --cov=app
```

**Frontend unit tests:**
```bash
cd frontend
npm test
```

**End-to-end** (requires Ollama + both servers running):
```bash
cd frontend
npm run test:e2e
```

## VS Code Setup

1. Install the [Continue extension](https://marketplace.visualstudio.com/items?itemName=Continue.continue)
2. Open this repo in VS Code — `.continue/config.json` is picked up automatically
3. `qwen3-coder` is set as the default model for inline suggestions and tab autocomplete

Use `@docs` in the Continue sidebar to reference files from `AI-Knowledge/`.

## Future Improvements

- **Qdrant vector store** — embed project files and docs for semantic search; load relevant context automatically into each prompt
- **OpenHands agent** — autonomous coding agent that reads tasks, writes code, runs tests, and reports results; add via `POST /api/agent/run` backed by the OpenHands Docker image
- **Conversation search** — full-text search across localStorage history; upgrade to IndexedDB for larger history
- **Multi-model routing** — route by task type automatically (e.g. long context → cloud, quick edits → local) based on message length or a classifier
- **Local speech-to-text** — Whisper.cpp integration for voice input; keep it fully local
- **Local text-to-speech** — Kokoro or Piper TTS for assistant voice responses
- **Prompt templates** — saved system prompts per assistant type (code reviewer, doc writer, architect)
- **File upload + RAG** — drag-and-drop files into chat; chunk and embed them on the fly for single-session retrieval
- **CI/CD integration** — GitHub Actions workflow that runs `pytest` and `vitest` on every push
- **Docker Compose** — single `docker compose up` to run backend, frontend dev server, and Qdrant together
- **Automated doc generation** — watch `AI-Knowledge/` for changes and re-embed into Qdrant on save
