# Copilot instructions — ERR (Ephemeral RAG Reader)

## Big picture
- Monorepo: `backend/` (FastAPI) + `frontend/` (Next.js 16 App Router).
- Core product constraint: **ephemeral, in-memory only**. No DB/filesystem persistence; sessions live in-process (`backend/app/session_store.py`).
- User flow:
  1) Frontend uploads a single document (`POST /upload`), then tails ingestion logs via SSE (`GET /api/logs/{session_id}`).
  2) Backend parses → chunks → embeds (OpenRouter) → builds **hybrid retriever** (FAISS + BM25) per session.
  3) Chat calls `POST /chat` and returns an answer + per-request citations (chunk list) to support clickable `[n]` citations.
  4) Export uses stable “global reference numbers” (`GET /export/{session_id}`) via `SessionState.register_references()`.

## Key files & patterns to follow
- API entrypoint: `backend/app/main.py` (routes, SSE generator, strict RAG prompting + guardrail retry).
- Strict-RAG enforcement: `backend/app/guardrails.py`.
  - The fallback string is **exactly**: `The document does not mention this.` (see `STRICT_NO_MENTION`).
  - Any non-fallback answer must include in-range citations like `[1][2]`.
- Session semantics: `backend/app/session_store.py`.
  - Upload overwrites session state (single-file mode): resets `chunks`, `retriever`, `chat_history`, `references`.
  - TTL is refreshed on access (`touch()`); cleanup loop runs in lifespan (`_cleanup_loop`).
- Ingestion: `backend/app/ingestion/file_parser.py` + `backend/app/ingestion/chunker.py`.
  - Chunk schema must stay aligned with frontend `frontend/lib/types.ts` and backend `backend/app/models/chunk.py`.
- Retrieval: `backend/app/retrieval/hybrid_retriever.py`.
  - Vector is cosine via L2-normalized `faiss.IndexFlatIP`.
  - Fusion: `final = 0.8 * vector_score + 0.2 * bm25_norm` (weights must sum to 1).
- OpenRouter integration: `backend/app/openrouter_client.py`.
  - Uses `/embeddings` + `/chat/completions` with retries; errors often live under payload `error.code/message`.

## Dev workflows (repo-specific)
- Backend env is loaded from `backend/.env` (or override with `ENV_FILE=...`): see `backend/app/config.py` and `backend/.env.example`.
- Run backend (from repo root): install `backend/requirements.txt`, then `uvicorn backend.app.main:app --reload --port 8000`.
- Run frontend: `cd frontend && npm install && cp .env.example .env.local && npm run dev`.
- Tests use `unittest` (no pytest dependency): `python -m unittest backend.tests.test_guardrails`.

## Frontend ↔ backend contract (don’t break)
- `UploadPanel` sends `X-Session-Id` if present; server returns/echoes `session_id` (`frontend/components/UploadPanel.tsx`).
- `TerminalWindow` treats any log line containing `Ready.` as success and `ERROR` as failure.
- Citation numbering must match context numbering in `backend/app/main.py::_build_context_blocks()` and the returned `citations` array (frontend enables citation buttons only when `1 <= n <= citations.length`).
