# AGENTS.md — ERR (Ephemeral RAG Reader)

This file provides essential context for AI coding agents working on the ERR project.

## Project Overview

**ERR (Ephemeral RAG Reader)** is a privacy-first document Q&A application with state-of-the-art hybrid retrieval. Users upload documents and ask questions with cited answers. All processing happens in-memory with automatic TTL cleanup — no database, no persistence.

- **Live URL**: https://bookembed.net
- **Repository**: Full-stack monorepo with backend (FastAPI) and frontend (React)
- **Language**: English codebase with bilingual documentation (EN/ZH)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (Vite + React + Ant Design)          │
│  ┌────────┐ ┌──────┐ ┌──────┐ ┌────────────┐ ┌────────────────┐ │
│  │ Upload │ │ Chat │ │ Logs │ │ Evaluation │ │ Citation View  │ │
│  └───┬────┘ └──┬───┘ └──┬───┘ └─────┬──────┘ └───────┬────────┘ │
└───────┼─────────────┼─────────────┼─────────────────┼───────────┘
        │             │             │                 │
        ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Session Store (In-Memory)                 ││
│  │  • Chunks + Embeddings    • FAISS Index    • BM25 Index     ││
│  │  • Chat History           • TTL Cleanup                      ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Retrieval Pipeline (Hybrid RAG)                ││
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐   ││
│  │  │  HyDE   │→ │ Multi-  │→ │ Hybrid  │→ │ LLM Rerank   │   ││
│  │  │         │  │ Query   │  │ Search  │  │ (optional)   │   ││
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────────┘   ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   OpenRouter API    │
                    │  • Qwen3 Embeddings │
                    │  • Gemini Chat      │
                    └─────────────────────┘
```

## Technology Stack

### Backend (`/backend/`)
- **Framework**: FastAPI (Python 3.12)
- **Server**: Uvicorn with auto-reload (dev)
- **Key Libraries**:
  - `faiss-cpu` — Vector similarity search
  - `bm25s` — BM25 keyword retrieval
  - `sentence-transformers` — Local embedding fallback
  - `spacy`, `jieba` — NLP tokenization
  - `ebooklib`, `python-docx` — Document parsing
  - `httpx`, `tenacity` — HTTP client with retries
  - `sse-starlette` — Server-Sent Events
- **External API**: OpenRouter (embeddings + chat)

### Frontend (`/frontend/`)
- **Framework**: React 18 + TypeScript 5
- **Build Tool**: Vite 8
- **UI Library**: Ant Design 5
- **State Management**: Zustand 5
- **Styling**: Less (CSS preprocessor)
- **Linting**: ESLint 9 + typescript-eslint

### DevOps
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Caddy (production)
- **CI/CD**: GitHub Actions (auto-deploy on push to main)
- **Server**: Tencent Cloud (Hong Kong), Ubuntu 24.04

## Project Structure

```
book-rag/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry, lifespan, CORS
│   │   ├── config.py               # Settings with env loading
│   │   ├── routes.py               # API endpoints (upload, chat, logs, export)
│   │   ├── openrouter_client.py    # OpenRouter API wrapper with retries
│   │   ├── session_store.py        # In-memory session management + TTL
│   │   ├── chat_pipeline.py        # RAG chat orchestration
│   │   ├── ingestion_pipeline.py   # Document ingestion workflow
│   │   ├── guardrails.py           # Citation enforcement
│   │   ├── repacking.py            # Context re-packing strategies
│   │   ├── deps.py                 # FastAPI dependencies
│   │   ├── ingestion/              # Document parsing & chunking
│   │   │   ├── file_parser.py      # .txt, .md, .docx, .epub, .mobi
│   │   │   └── chunker.py          # Token-based & semantic chunking
│   │   ├── models/
│   │   │   └── chunk.py            # Chunk data model
│   │   └── retrieval/              # Search & evaluation
│   │       ├── hybrid_retriever.py # FAISS + BM25 fusion
│   │       ├── fusion.py           # RRF fusion utilities
│   │       └── evaluation.py       # Retrieval metrics
│   ├── tests/                      # Unit tests (unittest framework)
│   ├── requirements.txt            # Direct dependencies
│   ├── constraints.txt             # Pinned versions
│   ├── Dockerfile                  # Python 3.12 slim
│   └── .env.example                # Configuration template
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── HeroSection.tsx     # Landing page
│   │   │   ├── UploadPanel.tsx     # File upload UI
│   │   │   ├── ChatPanel.tsx       # Chat interface
│   │   │   ├── DocumentPanel.tsx   # Document/chunk viewer
│   │   │   ├── TerminalWindow.tsx  # Log stream display
│   │   │   └── EvaluationPanel.tsx # Retrieval metrics
│   │   ├── lib/
│   │   │   ├── store.ts            # Zustand state management
│   │   │   └── types.ts            # TypeScript types
│   │   ├── App.tsx                 # Main app with responsive layout
│   │   ├── main.tsx                # Entry point
│   │   ├── theme.ts                # Ant Design dark theme
│   │   └── index.less              # Global styles
│   ├── index.html
│   ├── vite.config.ts              # Vite config with proxy
│   ├── tsconfig.json
│   ├── eslint.config.js
│   ├── package.json
│   ├── Dockerfile                  # Dev Dockerfile
│   └── Dockerfile.prod             # Multi-stage production build
├── docker-compose.yml              # Development orchestration
├── docker-compose.prod.yml         # Production orchestration
└── .github/workflows/deploy.yml    # CI/CD pipeline
```

## Build and Run Commands

### Development (Docker - Recommended)

```bash
# Configure API key
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENROUTER_API_KEY

# Start all services
docker compose up --build

# Access: http://localhost:3000
# Backend: http://localhost:8000
```

### Development (Manual)

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt -c constraints.txt

# Create .env from example, then:
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
# Access: http://localhost:3000
```

### Production Deployment

```bash
# Using docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d --build
```

**Important**: Backend must run with `UVICORN_WORKERS=1` because sessions and ingestion state are stored in-memory. Multiple workers would split memory across processes and break session-based flows.

## Testing Commands

### Backend Tests
```bash
cd backend
python -m unittest discover -s tests -p "test_*.py"

# Or from repo root:
python -m unittest discover -s backend/tests -p "test_*.py"
```

### Frontend Tests
```bash
cd frontend
npm run lint              # ESLint check
npm run build             # TypeScript + Vite build
npm run test:code-splitting   # Verify chunk splitting
npm run bench:tbt         # Lighthouse performance benchmark
```

### CI/CD Pipeline
The GitHub Actions workflow (`.github/workflows/deploy.yml`) runs on every push to `main`:
1. Quality checks: lint + build + unit tests
2. Deploy to production server via SSH
3. Health checks on both services

Required secrets: `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`

## Configuration

### Backend (`backend/.env`)

**Required:**
```bash
OPENROUTER_API_KEY=your_key_here
```

**Common Settings:**
```bash
# Model selection
OPENROUTER_CHAT_MODEL_SIMPLE=qwen/qwen3.5-35b-a3b
OPENROUTER_CHAT_MODEL_COMPLEX=qwen/qwen3.5-122b-a10b
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

# Session TTL (default: 30 min)
ERR_SESSION_TTL_SECONDS=1800

# Chunking
ERR_CHUNK_TARGET_TOKENS=512
ERR_CHUNK_OVERLAP_TOKENS=50

# Retrieval tuning
ERR_QUERY_FUSION_ENABLED=true
ERR_HYDE_ENABLED=true
ERR_LLM_RERANK_ENABLED=true

# Fast mode (lower latency, uses MRL 1024-dim)
ERR_EMBEDDING_DIM_FAST_MODE=1024
```

See `backend/.env.example` for all 40+ configuration options.

### Frontend (`frontend/.env.local`)

```bash
VITE_BACKEND_URL=http://localhost:8000
```

In Docker, the frontend uses `/backend` proxy path to communicate with the backend service.

## Code Style Guidelines

### Python (Backend)
- **Typing**: Full type hints required (`from __future__ import annotations`)
- **Imports**: Grouped as stdlib → third-party → local
- **Formatting**: Follow existing patterns (PEP 8 inspired)
- **Async**: Use `async`/`await` for I/O operations
- **Error Handling**: Explicit exception handling with meaningful messages

### TypeScript (Frontend)
- **Strict Mode**: Enabled (`strict: true` in tsconfig)
- **Imports**: Use `@/` alias for src-relative imports
- **Components**: Functional components with explicit return types
- **State**: Zustand for global state, React hooks for local state
- **Styling**: Inline styles for dynamic values, Less for globals

## Key Design Decisions

### In-Memory Architecture
- **No database** — all session data stored in Python memory
- Sessions auto-expire after TTL (default 30 min)
- Background cleanup task runs every 30 seconds
- **Implication**: Single-worker deployment only; restarts clear all data

### Hybrid Retrieval Pipeline
1. **HyDE** — Generate hypothetical answer for query expansion
2. **Multi-Query** — Generate 6-8 query variants
3. **Hybrid Search** — FAISS (vector) + BM25 (keyword) in parallel
4. **RRF Fusion** — Reciprocal Rank Fusion of results
5. **LLM Rerank** — Yes/no relevance judge (optional)
6. **Repacking** — Reverse order (most relevant near end)

### Fast Mode vs Accuracy Mode
- **Fast Mode**: Uses MRL 1024-dim embeddings, skips some pipeline steps
- **Accuracy Mode**: Full 4096-dim embeddings, complete pipeline
- Toggle controlled by UI switch

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/upload` | POST | Upload document (multipart/form-data) |
| `/api/logs/{session_id}` | GET | SSE stream of ingestion logs |
| `/chat` | POST | Chat with RAG (JSON) |
| `/evaluation` | GET | Get retrieval evaluation metrics |
| `/export/{session_id}` | GET | Export chat history as Markdown |

## Security Considerations

1. **API Keys**: Stored in `.env` (never commit); loaded via `ENV_FILE` env var
2. **CORS**: Restricted to `localhost:3000` in development
3. **Session IDs**: UUID v4, passed via `X-Session-Id` header
4. **No Persistence**: Documents are not stored; only processed in memory
5. **Production**: HTTPS via Caddy with automatic Let's Encrypt

## Common Development Tasks

### Adding a New Endpoint
1. Add route in `backend/app/routes.py`
2. Add types in `backend/app/models/` if needed
3. Add tests in `backend/tests/`
4. Call from frontend via store or component

### Adding a New Component
1. Create in `frontend/src/components/`
2. Export from lazy loader in `App.tsx` if needed for code-splitting
3. Use Zustand store for state shared across components

### Modifying Configuration
1. Add field to `Settings` class in `backend/app/config.py`
2. Add env loader logic
3. Update `backend/.env.example` with documentation
4. Add test in `test_config_defaults_consistency.py`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENROUTER_API_KEY is not set` | Create `backend/.env` from `.env.example` |
| Port already in use | Change `--port` or update `VITE_BACKEND_URL` |
| FAISS import errors | Ensure `libgomp1` is installed (in Dockerfile) |
| Frontend can't reach backend | Check `VITE_BACKEND_URL` and CORS settings |
| Session lost on refresh | Expected — sessions are in-memory only |

## External Dependencies

- **OpenRouter**: Requires valid API key for all LLM/embedding operations
- **Hugging Face**: Downloads sentence-transformer models for local semantic chunking (if enabled)
- **PyPI**: Uses Tsinghua mirror by default in Docker for China region

---

*Last updated: 2026-02-16*
