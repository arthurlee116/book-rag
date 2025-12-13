# Repository Guidelines

## Project Overview

ERR (Ephemeral RAG Reader) is a privacy-first document Q&A web app. Users upload a document, the backend parses and chunks it, builds in-memory retrieval indexes (vector + BM25), and the frontend provides a chat UI that answers questions strictly using retrieved passages. “Ephemeral” is intentional: ingestion artifacts and chat state are per-session in memory with TTL cleanup; nothing is written to a database by default.

## Project Structure & Module Organization

- `backend/`: FastAPI service (Python). Core code lives in `backend/app/`:
  - `backend/app/main.py`: app lifecycle, CORS, routes, ingestion and chat orchestration.
  - `backend/app/config.py`: `Settings` and env loading (supports `ENV_FILE=/path/to/.env`).
  - `backend/app/openrouter_client.py`: OpenRouter HTTP wrapper for chat + embeddings.
  - `backend/app/session_store.py`: in-memory sessions, locks, TTL cleanup.
  - `backend/app/ingestion/`: file parsing and chunking (`file_parser.py`, `chunker.py`).
  - `backend/app/retrieval/`: hybrid retriever and indexing (`hybrid_retriever.py`).
  - `backend/app/guardrails.py`: strict answer enforcement (citations / fallback behavior).
- `frontend/`: Next.js 16 + React + TypeScript UI:
  - `frontend/app/`: App Router pages/layouts; main UI entrypoints.
  - `frontend/components/`: UI components (upload, chat, logs/status panels).
  - `frontend/lib/`: API helpers, state, and shared utilities.

Keep boundaries clear: the frontend talks to the backend over HTTP using `NEXT_PUBLIC_BACKEND_URL`; do not share runtime code across the boundary.

## Architecture & Request Flow

1. Frontend starts at `http://localhost:3000` and reads `NEXT_PUBLIC_BACKEND_URL` from `frontend/.env.local`.
2. A session is identified via an HTTP header (the backend accepts an `X-Session-Id` style header); if missing, a new session is created server-side.
3. Upload:
   - The frontend uploads a document to the backend (`POST /upload`).
   - The backend parses it into text “blocks”, then chunks blocks into ~500-token chunks.
   - The backend calls OpenRouter embeddings in batches and builds in-memory indexes: FAISS for vectors and BM25 for lexical matching.
   - Ingestion logs are streamed over Server-Sent Events (`GET /api/logs/{session_id}`) to show progress in the UI.
4. Chat:
   - The frontend sends a user question; the backend embeds the query (with optional instruction templating), retrieves candidate chunks via hybrid retrieval, then calls the chat model with strict constraints.
   - The backend post-processes the model output using guardrails to enforce citation behavior.

## Build, Test, and Development Commands

From repo root:

- Backend setup: `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`
- Backend run (dev): `uvicorn backend.app.main:app --reload --port 8000`
- Backend health check: `curl http://localhost:8000/health`
- Backend tests (unit): `python -m unittest discover -s backend/tests -p "test_*.py"`

From `frontend/`:

- Install deps: `npm install`
- Dev server: `npm run dev` (serves on http://localhost:3000)
- Lint: `npm run lint` (ESLint flat config)
- Production build: `npm run build && npm run start`

Tip: run backend first, then frontend. If the backend port changes, update `frontend/.env.local`.

## Coding Style & Naming Conventions

- Python:
  - 4-space indentation, type hints preferred, and predictable error handling for API routes.
  - Keep imports lightweight at package import time so tooling can run without heavy deps (see `backend/app/models/__init__.py`).
  - Prefer small, pure helpers for parsing/chunking/retrieval so they’re testable without spinning up FastAPI.
- TypeScript/React:
  - Keep TypeScript `strict` enabled (`frontend/tsconfig.json`); avoid `any`.
  - Follow ESLint rules in `frontend/eslint.config.mjs` (React hooks rules + Next core-web-vitals).
  - Use the `@/*` path alias for imports when helpful.
- Naming:
  - Python: `snake_case` for functions/vars, `PascalCase` for classes.
  - React: components `PascalCase`, hooks `useThing`, event handlers `onThing`.

## Testing Guidelines

- Backend uses `unittest` (`backend/tests/`) with discovery. Keep tests fast and deterministic.
- Name tests `test_*.py` and test public helpers (e.g., guardrails, retrieval scoring behavior, token estimation).
- If a change affects API contracts (request/response shape, headers, status codes), add a unit test and update the frontend caller accordingly.

## Commit & Pull Request Guidelines

- Commits follow Conventional Commits (e.g., `feat: ...`, `fix: ...`). Keep subjects imperative and scoped (example: `feat(ingestion): support .docx headings`).
- PRs should include:
  - Summary: what changed and why (1–2 paragraphs).
  - Testing notes: commands run and manual checks performed.
  - UI changes: screenshots or a short screen recording.
  - Configuration changes: note any added/renamed env vars and update `.env.example` files when appropriate.

## Security & Configuration Tips

- Never commit secrets. Use `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env.local`.
- Backend env highlights (see `backend/.env.example`):
  - `OPENROUTER_API_KEY`: required for embeddings/chat.
  - `OPENROUTER_CHAT_MODEL`, `OPENROUTER_EMBEDDING_MODEL`: model selection.
  - `OPENROUTER_EMBEDDING_DIM`: expected dim (backend can warn on mismatch).
  - `ERR_SESSION_TTL_SECONDS`, `ERR_SESSION_CLEANUP_INTERVAL_SECONDS`: in-memory session lifecycle.
  - `ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS`: guardrail against oversized prompts.
  - `ERR_EMBEDDING_QUERY_*`: instruction templating for retrieval.
- Treat uploaded documents as sensitive:
  - Keep processing in-memory unless explicitly changing the privacy model.
  - Be careful when adding logging; avoid writing raw document text or user queries to disk.

## Troubleshooting

- `OPENROUTER_API_KEY is not set`: ensure `backend/.env` exists and contains `OPENROUTER_API_KEY=...` or export it in your shell.
- Frontend cannot reach backend: confirm `NEXT_PUBLIC_BACKEND_URL` in `frontend/.env.local` matches the running backend (default `http://localhost:8000`).
- Port conflict: run `uvicorn ... --port 8001` and update `frontend/.env.local`.
- Slow ingestion: large documents embed in batches; optimize chunk size, batch size, or model choice first.
