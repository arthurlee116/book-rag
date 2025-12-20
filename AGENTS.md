# Repository Guidelines

## Project Overview

ERR (Ephemeral RAG Reader) is a privacy-first document Q&A web app. Users upload a document, the backend parses and chunks it, builds in-memory retrieval indexes (vector + BM25), and the frontend provides a chat UI that answers questions strictly using retrieved passages. "Ephemeral" is intentional: ingestion artifacts and chat state are per-session in memory with TTL cleanup; nothing is written to a database by default.

## Project Structure & Module Organization

- `backend/`: FastAPI service (Python). Core code lives in `backend/app/`:
  - `backend/app/main.py`: app lifecycle, CORS, routes, ingestion and chat orchestration.
  - `backend/app/config.py`: `Settings` and env loading (supports `ENV_FILE=/path/to/.env`).
  - `backend/app/openrouter_client.py`: OpenRouter HTTP wrapper for chat + embeddings.
  - `backend/app/session_store.py`: in-memory sessions, locks, TTL cleanup.
  - `backend/app/ingestion/`: file parsing and chunking (`file_parser.py`, `chunker.py`).
  - `backend/app/retrieval/`: hybrid retriever, indexing, and evaluation metrics (`hybrid_retriever.py`, `evaluation.py`).
  - `backend/app/guardrails.py`: strict answer enforcement (citations / fallback behavior).
- `frontend/`: Vite + React + Ant Design + TypeScript UI:
  - `frontend/src/main.tsx`: React entry point with Ant Design ConfigProvider.
  - `frontend/src/App.tsx`: main application component.
  - `frontend/src/theme.ts`: Ant Design dark theme token configuration.
  - `frontend/src/components/`: UI components (UploadPanel, ChatPanel, TerminalWindow, DocumentPanel, EvaluationPanel).
  - `frontend/src/lib/`: Zustand state (`store.ts`) and TypeScript types (`types.ts`).
  - `frontend/vite.config.ts`: Vite configuration with API proxy.

Keep boundaries clear: the frontend talks to the backend over HTTP using `VITE_BACKEND_URL`; do not share runtime code across the boundary.

## Architecture & Request Flow

1. Frontend starts at `http://localhost:3000` and reads `VITE_BACKEND_URL` from `frontend/.env.local`.
2. A session is identified via an HTTP header (the backend accepts an `X-Session-Id` style header); if missing, a new session is created server-side.
3. Upload:
   - The frontend uploads a document to the backend (`POST /upload`).
   - The backend parses it into text "blocks", then builds sentence-based chunks (target ~512 tokens with overlap; optional semantic splits via sentence embeddings).
   - The backend calls OpenRouter embeddings in batches and builds in-memory indexes: FAISS for vectors and BM25 for lexical matching.
   - Ingestion logs are streamed over Server-Sent Events (`GET /api/logs/{session_id}`) to show progress in the UI.
4. Chat (Normal Mode):
   - The frontend sends a user question; the backend runs the full retrieval pipeline:
     1. Language alignment (translate query to document language if needed)
     2. Multi-query expansion (generate 6 query variants using `chat_model_complex`)
     3. HyDE (generate hypothetical passage using `chat_model_simple`)
     4. Hybrid search (FAISS + BM25) per query variant
     5. RRF fusion (merge rankings with k=60)
     6. Drift filtering (remove off-topic variants)
     7. LLM rerank (judge relevance using `chat_model_complex`)
     8. Re-packing (reorder chunks, default: reverse)
   - The backend generates the answer using `chat_model_simple` with strict RAG constraints.
   - The backend post-processes the model output using guardrails to enforce citation behavior.
5. Chat (Fast Mode):
   - Uses 1024-dim MRL embeddings instead of 4096
   - Skips multi-query expansion, HyDE, and LLM rerank
   - Faster but potentially lower recall

## Build, Test, and Development Commands

From repo root:

- Backend setup: `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`
- Backend run (dev): `uvicorn backend.app.main:app --reload --port 8000`
- Backend health check: `curl http://localhost:8000/health`
- Backend tests (unit): `python -m unittest discover -s backend/tests -p "test_*.py"`

From `frontend/`:

- Install deps: `npm install --legacy-peer-deps`
- Dev server: `npm run dev` (serves on http://localhost:3000)
- Lint: `npm run lint`
- Production build: `npm run build`
- Preview production build: `npm run preview`

Tip: run backend first, then frontend. If the backend port changes, update `frontend/.env.local`.

## Coding Style & Naming Conventions

- Python:
  - 4-space indentation, type hints preferred, and predictable error handling for API routes.
  - Keep imports lightweight at package import time so tooling can run without heavy deps (see `backend/app/models/__init__.py`).
  - Prefer small, pure helpers for parsing/chunking/retrieval so they're testable without spinning up FastAPI.
- TypeScript/React:
  - Keep TypeScript `strict` enabled (`frontend/tsconfig.json`); avoid `any`.
  - Follow ESLint rules in `frontend/eslint.config.js`.
  - Use the `@/*` path alias for imports (maps to `src/*`).
  - Use Ant Design components for UI; customize via `theme.ts` tokens.
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
  - `OPENROUTER_CHAT_MODEL_SIMPLE`: model for simple tasks (translation, HyDE, QA generation). Default: `google/gemini-2.5-flash-lite-preview-09-2025`
  - `OPENROUTER_CHAT_MODEL_COMPLEX`: model for complex tasks (multi-query expansion, LLM rerank). Default: `google/gemini-2.5-flash-preview-09-2025`
  - `OPENROUTER_EMBEDDING_MODEL`: embedding model selection. Default: `qwen/qwen3-embedding-8b`
  - `OPENROUTER_EMBEDDING_DIM`: expected dim (backend can warn on mismatch). Default: `4096`
  - `ERR_SESSION_TTL_SECONDS`, `ERR_SESSION_CLEANUP_INTERVAL_SECONDS`: in-memory session lifecycle.
  - `ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS`: guardrail against oversized prompts.
  - `ERR_EMBEDDING_QUERY_*`: instruction templating for retrieval.
  - `ERR_QUERY_FUSION_ENABLED`, `ERR_HYDE_ENABLED`, `ERR_LLM_RERANK_ENABLED`: retrieval pipeline toggles.
  - `ERR_REPACK_STRATEGY`: context ordering ("reverse" or "forward").
  - `ERR_EMBEDDING_DIM_FAST_MODE`: MRL dimension for fast mode (default: 1024).
- Frontend env highlights (see `frontend/.env.example`):
  - `VITE_BACKEND_URL`: backend API URL. Default: `http://localhost:8000`
- **Note:** `OPENROUTER_CHAT_MODEL` and `NEXT_PUBLIC_BACKEND_URL` are deprecated and no longer used.
- Treat uploaded documents as sensitive:
  - Keep processing in-memory unless explicitly changing the privacy model.
  - Be careful when adding logging; avoid writing raw document text or user queries to disk.

## Production Deployment

### Server Info
- **Domain**: https://bookembed.net
- **Server**: Tencent Cloud (Hong Kong)
- **IP**: 43.159.200.246
- **OS**: Ubuntu 24.04
- **User**: ubuntu

### Key Files on Server
- Project: `~/book-rag`
- Caddy config: `/etc/caddy/Caddyfile`
- Docker Compose: `docker-compose.prod.yml`

### Caddy Reverse Proxy
Caddy handles HTTPS (auto Let's Encrypt) and routes:
- `https://bookembed.net/*` → frontend (localhost:3000)
- `https://bookembed.net/backend/*` → backend (localhost:8000, with `/backend` prefix stripped)

### Deployment Commands
```bash
# SSH to server
ssh ubuntu@43.159.200.246

# Update and redeploy
cd ~/book-rag && git pull && sudo docker compose -f docker-compose.prod.yml up -d --build

# View logs
sudo docker compose -f ~/book-rag/docker-compose.prod.yml logs -f

# Restart services
sudo docker compose -f ~/book-rag/docker-compose.prod.yml restart

# Check Caddy
sudo systemctl status caddy
sudo systemctl restart caddy
```

### Important Notes
- The `docker-compose.prod.yml` frontend service should NOT have a `command:` override; use Dockerfile.prod's CMD (`serve -s dist -l 3000`).
- Frontend build requires `VITE_BACKEND_URL=/backend` in `.env.production` (handled by Dockerfile.prod ARG).
- Backend `.env` must be copied separately (not in git): `scp backend/.env ubuntu@43.159.200.246:~/book-rag/backend/.env`

### CI/CD Automatic Deployment

GitHub Actions automatically deploys on every push to `main`:

**Workflow**: `.github/workflows/deploy.yml`
- SSH to server using `DEPLOY_SSH_KEY` secret
- Pull latest code from GitHub
- Rebuild and restart Docker containers
- Health check both frontend and backend endpoints

**GitHub Secrets** (configured via `gh secret set`):
- `DEPLOY_HOST`: Server IP (43.159.200.246)
- `DEPLOY_USER`: SSH username (ubuntu)
- `DEPLOY_SSH_KEY`: Server's `~/.ssh/github_actions_deploy` private key

**Server Setup**:
- Deployment key: `~/.ssh/github_actions_deploy` (ed25519)
- Public key added to `~/.ssh/authorized_keys`

Manual deployment is still available via SSH commands above.

## Troubleshooting

- `OPENROUTER_API_KEY is not set`: ensure `backend/.env` exists and contains `OPENROUTER_API_KEY=...` or export it in your shell.
- Frontend cannot reach backend: confirm `VITE_BACKEND_URL` in `frontend/.env.local` matches the running backend (default `http://localhost:8000`).
- Port conflict: run `uvicorn ... --port 8001` and update `frontend/.env.local`.
- Slow ingestion: large documents embed in batches; optimize chunk size, batch size, or model choice first.
- Production frontend not connecting to backend: ensure `VITE_BACKEND_URL=/backend` is set during build, and Caddy is properly configured to proxy `/backend/*` to the backend service.
