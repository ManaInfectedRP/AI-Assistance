# AIAssistance

Local-first AI assistant with general chat and coding assistance. Runs entirely on your machine via Ollama — no cloud required for daily use.

## Stack

- **Frontend:** React + TypeScript (Vite), streaming SSE via `fetch`
- **Backend:** Python FastAPI, provider abstraction for Ollama / cloud models
- **Models:** `qwen3` (general chat), `qwen3-coder` (coding assistance)
- **VS Code:** Continue extension with `qwen3-coder` as default

## Quick Start

### Prerequisites
- [Ollama](https://ollama.com/download) installed and running
- Node.js 18+ and Python 3.11+

### 1. Pull models
```bash
ollama pull qwen3
ollama pull qwen3-coder
```

### 2. Backend
```bash
cd backend
python -m 3.11 venv venv
venv/Scripts/activate      # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Structure

```
AIAssistance/
├── backend/          FastAPI + Ollama proxy
├── frontend/         React + TypeScript chat UI
├── AI-Knowledge/     Project docs loaded into Continue context
└── .continue/        VS Code Continue extension config
```
