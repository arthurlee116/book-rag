# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ERR (Ephemeral RAG Reader) is a privacy-first, session-based document Q&A webapp. Users upload a single document, the backend parses and chunks it, builds in-memory retrieval indexes (vector + BM25), and the frontend provides a chat UI that answers questions strictly using retrieved passages. "Ephemeral" means all ingestion artifacts and chat state are stored per-session in memory and cleaned up on TTL - nothing is written to a database.

## Development Commands

### Backend (FastAPI + Python)
```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENROUTER_API_KEY

# Run development server
uvicorn backend.app.main:app --reload --port 8000

# Health check
curl http://localhost:8000/health

# Run tests
python -m unittest discover -s backend/tests -p "test_*.py"
```

### Frontend (Next.js 16 + TypeScript)
```bash
# Setup (from frontend/ directory)
cd frontend
npm install

# Configure environment
cp .env.example .env.local
# Edit NEXT_PUBLIC_BACKEND_URL if backend runs on different port

# Development server
npm run dev  # Serves on http://localhost:3000

# Linting
npm run lint

# Production build
npm run build && npm run start
```

## Architecture & Key Components

### Backend Architecture (`backend/app/`)
- **Main Application**: [`main.py`](backend/app/main.py) - FastAPI app lifecycle, CORS, routes, ingestion/chat orchestration
- **Configuration**: [`config.py`](backend/app/config.py) - Settings and env loading (supports `ENV_FILE=/path/to/.env`)
- **OpenRouter Client**: [`openrouter_client.py`](backend/app/openrouter_client.py) - HTTP wrapper for chat + embeddings
- **Session Store**: [`session_store.py`](backend/app/session_store.py) - In-memory sessions, locks, TTL cleanup
- **Ingestion Pipeline**:
  - [`ingestion/file_parser.py`](backend/app/ingestion/file_parser.py) - Multi-format document parser (epub, mobi, docx, txt, md)
  - [`ingestion/chunker.py`](backend/app/ingestion/chunker.py) - Sentence-based chunking with token targets, overlap, and optional semantic splits
- **Retrieval System**: [`retrieval/hybrid_retriever.py`](backend/app/retrieval/hybrid_retriever.py) - FAISS + BM25 hybrid search with fusion
- **Guardrails**: [`guardrails.py`](backend/app/guardrails.py) - Strict RAG answer enforcement with citations

### Frontend Architecture (`frontend/`)
- **App Router**: [`app/`](frontend/app/) - Next.js 16 App Router pages and layouts
- **Components**: [`components/`](frontend/components/) - React UI components (upload, chat, terminal, etc.)
- **State Management**: [`lib/store.ts`](frontend/lib/store.ts) - Zustand store for session, upload status, chat history
- **API Layer**: HTTP client backend communication using `NEXT_PUBLIC_BACKEND_URL`

### Request Flow
1. **Session Management**: Sessions identified via `X-Session-Id` header; new sessions created server-side if missing
2. **Document Upload**: `POST /upload` → parse → chunk → embed → build indexes → stream logs via SSE
3. **Chat**: `POST /chat` → query expansion (optional) → hybrid retrieval → strict RAG generation → guardrails enforcement
4. **Real-time Logs**: `GET /api/logs/{session_id}` - Server-Sent Events for ingestion progress

## Key Technical Details

### Chunk Data Structure
Each chunk includes:
- `id`, `content`, `rich_content`
- `prev_content`/`next_content` for context
- `metadata` with chapter/heading information when available

### Hybrid Retrieval
- **Vector Search**: FAISS with cosine similarity (embeddings from qwen/qwen3-embedding-8b, dim=4096)
- **Lexical Search**: BM25 with language-specific tokenization (jieba for Chinese, spacy for English)
- **Fusion**: Weighted combination (0.8 vector + 0.2 BM25) with per-query MinMax normalization

### Advanced Retrieval Pipeline (Normal Mode)
The full retrieval pipeline includes several optional stages:
1. **Language Alignment**: Translate query to document language if needed (uses `chat_model_simple`)
2. **Multi-Query Expansion**: Generate 6 query variants for better recall (uses `chat_model_complex`)
3. **HyDE**: Generate hypothetical passage to improve semantic matching (uses `chat_model_simple`)
4. **Hybrid Search**: FAISS + BM25 per query variant
5. **RRF Fusion**: Reciprocal Rank Fusion to merge rankings from all variants (k=60)
6. **Drift Filtering**: Remove off-topic query variants (similarity threshold: 0.25)
7. **LLM Rerank**: Judge passage relevance with LLM (uses `chat_model_complex`)
8. **Re-packing**: Reorder chunks (default: reverse, best chunks near query for attention)

### Fast Mode
Toggle fast mode for quicker responses with reduced accuracy:
- Uses 1024-dim MRL embeddings instead of 4096
- Disables multi-query expansion, HyDE, and LLM rerank
- Uses simple mean for embedding aggregation

### Strict RAG Enforcement
- Answers must be based solely on retrieved document passages
- If document doesn't contain answer: "The document does not mention this."
- Citations format: `[1][2]` stacked numbers referencing chunk IDs
- Context limit guard: ~32k tokens with hard cutoff

## Environment Configuration

### Required Backend Environment Variables
- `OPENROUTER_API_KEY` - OpenRouter API key for embeddings/chat models
- `OPENROUTER_CHAT_MODEL_SIMPLE` - Model for simple tasks (translation, HyDE, QA). Default: `google/gemini-2.5-flash-lite-preview-09-2025`
- `OPENROUTER_CHAT_MODEL_COMPLEX` - Model for complex tasks (multi-query expansion, LLM rerank). Default: `google/gemini-2.5-flash-preview-09-2025`
- `OPENROUTER_EMBEDDING_MODEL` - Default: `qwen/qwen3-embedding-8b`
- `OPENROUTER_EMBEDDING_DIM` - Default: `4096`

> **Note:** `OPENROUTER_CHAT_MODEL` is deprecated and no longer used.

### Optional Backend Settings
- `ERR_SESSION_TTL_SECONDS` - Session inactivity timeout (default: 1800s)
- `ERR_SESSION_CLEANUP_INTERVAL_SECONDS` - Cleanup interval (default: 30s)
- `ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS` - Context limit guard (default: 32768)
- `ERR_EMBEDDING_QUERY_USE_INSTRUCTION` - Enable instruction-based embeddings (default: true)
- `ERR_EMBEDDING_QUERY_INSTRUCTION_TEMPLATE` - Template for embedding instructions
- `ERR_EMBEDDING_DIM_FAST_MODE` - MRL dimension for fast mode (default: 1024)
- `ERR_QUERY_FUSION_ENABLED` - Enable multi-query expansion (default: true)
- `ERR_HYDE_ENABLED` - Enable hypothetical document embedding (default: true)
- `ERR_LLM_RERANK_ENABLED` - Enable LLM-based reranking (default: true)
- `ERR_REPACK_STRATEGY` - Context ordering: "reverse" (best at end) or "forward" (default: reverse)

### Frontend Environment
- `NEXT_PUBLIC_BACKEND_URL` - Backend API base URL (default: `http://localhost:8000`)

## File Format Support
- **Documents**: `.epub`, `.mobi`, `.docx`, `.txt`, `.md`
- **Parsing Strategy**: Extract text content while preserving chapter/heading structure in metadata
- **Chunking**: Sentence-based, target ~512 tokens with overlap and optional semantic splits; prev/next context retained

## Security & Privacy Considerations
- All document processing happens in-memory only
- No persistence of uploaded documents or chat history
- Sessions automatically expire and are cleaned up
- Be careful when adding logging to avoid writing document text or queries to disk
- Never commit API keys or sensitive configuration

## Development Notes
- Use Python 4-space indentation, type hints preferred
- Keep TypeScript `strict` enabled, avoid `any` types
- Follow conventional commits (`feat:`, `fix:`, etc.)
- Frontend uses `@/*` path alias for imports when it improves clarity
- Run backend first, then frontend during development

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

### Caddy Reverse Proxy Configuration
Caddy handles HTTPS (auto Let's Encrypt) with this config (`/etc/caddy/Caddyfile`):
```
bookembed.net {
    reverse_proxy localhost:3000

    handle /backend/* {
        uri strip_prefix /backend
        reverse_proxy localhost:8000
    }
}
```

Routes:
- `https://bookembed.net/*` → frontend (localhost:3000)
- `https://bookembed.net/backend/*` → backend (localhost:8000, `/backend` prefix stripped)

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
- Frontend build requires `VITE_BACKEND_URL=/backend` (handled by Dockerfile.prod ARG creating `.env.production`).
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
