# Backend (ERR)

FastAPI backend for ERR (Ephemeral RAG Reader). Handles file upload + ingestion, builds in-memory indexes, and serves chat/retrieval APIs to the Next.js frontend.

## Requirements

- Python 3.10+ recommended
- Node.js is only needed for the frontend

## Setup

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Configure environment

Create a local env file (not committed):

```bash
cp backend/.env.example backend/.env
```

Set at least:

- `OPENROUTER_API_KEY` — your OpenRouter API key

Notes:

- The backend auto-loads env values from `backend/.env` when starting.
- You can override the env file path via `ENV_FILE=/path/to/.env`.

## Run the server

From the repo root (recommended):

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

## Useful endpoints

- `GET /health` — basic health check
- `POST /upload` — upload a document for ingestion (frontend uses this)
- `GET /api/logs/{session_id}` — Server-Sent Events stream of ingestion logs

## Troubleshooting

- `OPENROUTER_API_KEY is not set`
  - Ensure `backend/.env` exists and contains `OPENROUTER_API_KEY=...`, or export it in your shell.
- Port already in use
  - Change with `--port 8000` → `--port 8001` and update `frontend/.env.local` (`NEXT_PUBLIC_BACKEND_URL`).

