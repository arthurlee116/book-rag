<p align="center">
  <img src="https://img.shields.io/badge/Privacy-First-green?style=for-the-badge" alt="Privacy First"/>
  <img src="https://img.shields.io/badge/RAG-Hybrid%20Retrieval-blue?style=for-the-badge" alt="Hybrid RAG"/>
  <img src="https://img.shields.io/badge/Embedding-Qwen3--8B-purple?style=for-the-badge" alt="Qwen3 Embedding"/>
</p>

<h1 align="center">📚 ERR — Ephemeral RAG Reader</h1>

<p align="center">
  <strong>Privacy-first document Q&A with state-of-the-art hybrid retrieval</strong>
</p>

<p align="center">
  Upload a document → Ask questions → Get cited answers<br/>
  <em>Everything stays in memory. Nothing is stored. Your data is yours.</em>
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **Privacy-First** | All processing happens in-memory with automatic TTL cleanup. No database, no persistence. |
| 🎯 **Hybrid Retrieval** | Combines FAISS vector search + BM25 keyword matching for superior recall |
| 🧠 **Qwen3-Embedding-8B** | MTEB #1 multilingual embedding model with MRL (Matryoshka) support |
| 📝 **Strict Citations** | Every answer includes `[1][2]` style citations linking to source passages |
| ⚡ **Fast Mode** | Toggle between accuracy (full pipeline) and speed (MRL 1024-dim search) |
| 🌍 **100+ Languages** | Full multilingual support inherited from Qwen3 |
| 📄 **Multiple Formats** | Supports `.txt`, `.md`, `.docx`, `.epub`, `.mobi` |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 16)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Upload  │  │   Chat   │  │   Logs   │  │ Citation Viewer  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘ │
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
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────────┐  │
│  │              Retrieval Pipeline                            │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐  │  │
│  │  │  HyDE   │→ │ Multi-  │→ │ Hybrid  │→ │ LLM Rerank   │  │  │
│  │  │         │  │ Query   │  │ Search  │  │ (optional)   │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └──────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   OpenRouter API    │
                    │  • Embeddings       │
                    │  • Chat Completion  │
                    └─────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 20.9+** (Next.js 16 requirement)
- **OpenRouter API Key** — [Get one here](https://openrouter.ai/keys)

### Option 1: Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/yourusername/book-rag.git
cd book-rag

# 2. Configure your API key
cp backend/.env.example backend/.env
# Edit backend/.env and set OPENROUTER_API_KEY=your_key_here

# 3. Start everything
docker compose up --build

# 4. Open http://localhost:3000
```

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

uvicorn backend.app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) 🎉

## 📖 How It Works

### 1. Document Ingestion

When you upload a document:

1. **Parse** — Extract text blocks from `.txt`, `.md`, `.docx`, `.epub`, or `.mobi`
2. **Chunk** — Split into ~512-token chunks with 50-token overlap for context continuity
3. **Embed** — Generate 4096-dim vectors using Qwen3-Embedding-8B via OpenRouter
4. **Index** — Build FAISS (vector) + BM25 (keyword) indexes in memory

### 2. Query Processing (Normal Mode)

```
User Query
    │
    ├─→ Language Alignment (translate if needed)
    │
    ├─→ Query Expansion
    │   ├─→ Generate 6 query variants (Multi-Query)
    │   └─→ Generate hypothetical passage (HyDE)
    │
    ├─→ Embed all variants (instruction-aware)
    │
    ├─→ Hybrid Search (per variant)
    │   ├─→ FAISS: top-50 by vector similarity
    │   └─→ BM25: top-50 by keyword match
    │
    ├─→ RRF Fusion (combine all rankings)
    │
    ├─→ LLM Rerank (judge relevance)
    │
    ├─→ Re-pack (reverse order for attention)
    │
    └─→ Generate Answer (with citations)
```

### 3. Fast Mode

Toggle "Fast Mode" for quicker responses:

| Feature | Normal Mode | Fast Mode |
|---------|-------------|-----------|
| Search Dimension | 4096 | 1024 (MRL) |
| Query Expansion | ✅ Multi-Query + HyDE | ❌ |
| LLM Rerank | ✅ | ❌ |
| Re-packing | ✅ Reverse | ❌ |
| Embedding Aggregation | Weighted | Simple Mean |

## ⚙️ Configuration

All settings are in `backend/.env`. Key options:

```bash
# Models
# Simple tasks (translation, HyDE, QA) - use lighter/faster model
OPENROUTER_CHAT_MODEL_SIMPLE=google/gemini-2.5-flash-lite-preview-09-2025
# Complex tasks (multi-query expansion, LLM rerank) - use more capable model
OPENROUTER_CHAT_MODEL_COMPLEX=google/gemini-2.5-flash-preview-09-2025
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b

# Retrieval Pipeline
ERR_QUERY_FUSION_ENABLED=true      # Multi-query expansion
ERR_HYDE_ENABLED=true              # Hypothetical document embedding
ERR_LLM_RERANK_ENABLED=true        # LLM-based reranking
ERR_REPACK_STRATEGY=reverse        # Put best chunks near query

# Performance
ERR_EMBEDDING_DIM_FAST_MODE=1024   # MRL dimension for fast mode
ERR_SESSION_TTL_SECONDS=1800       # Session timeout (30 min)
```

> **Note:** `OPENROUTER_CHAT_MODEL` is deprecated and no longer used. Use `OPENROUTER_CHAT_MODEL_SIMPLE` and `OPENROUTER_CHAT_MODEL_COMPLEX` instead.

See [`backend/.env.example`](backend/.env.example) for all options.

## 🧪 Testing

```bash
# Backend unit tests
cd backend
python -m unittest discover -s tests -p "test_*.py"

# Frontend lint
cd frontend
npm run lint
```

## 📁 Project Structure

```
book-rag/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, routes, orchestration
│   │   ├── config.py            # Settings & env loading
│   │   ├── openrouter_client.py # OpenRouter API wrapper
│   │   ├── session_store.py     # In-memory session management
│   │   ├── guardrails.py        # Citation enforcement
│   │   ├── ingestion/
│   │   │   ├── file_parser.py   # Document parsing
│   │   │   └── chunker.py       # Text chunking with overlap
│   │   └── retrieval/
│   │       └── hybrid_retriever.py  # FAISS + BM25 hybrid search
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── app/                     # Next.js App Router
│   ├── components/
│   │   ├── UploadPanel.tsx      # File upload UI
│   │   ├── ChatPanel.tsx        # Chat interface
│   │   └── TerminalWindow.tsx   # Ingestion logs
│   └── lib/
│       ├── store.ts             # Zustand state
│       └── types.ts             # TypeScript types
├── docker-compose.yml           # Dev environment
└── docker-compose.prod.yml      # Production-like setup
```

## 🔬 Technical Highlights

### Qwen3-Embedding-8B

We use the **#1 ranked model on MTEB Multilingual** (score: 70.58 as of June 2025):

- **4096 dimensions** (full) or **1024 dimensions** (MRL fast mode)
- **Instruction-aware** — queries use task-specific prompts for +1-5% accuracy
- **100+ languages** including code
- **32K context** for long documents

### Hybrid Retrieval

Combines the best of both worlds:

- **FAISS (Dense)** — Semantic similarity via cosine distance
- **BM25 (Sparse)** — Keyword matching for exact terms
- **RRF Fusion** — Reciprocal Rank Fusion to merge rankings

### Privacy by Design

- **No database** — Everything lives in memory
- **TTL cleanup** — Sessions auto-expire after 30 minutes
- **No logging of content** — Document text never hits disk

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit with [Conventional Commits](https://www.conventionalcommits.org/) (`git commit -m 'feat: add amazing feature'`)
4. Push and open a PR

## 📄 License

[Apache 2.0](LICENSE)

---

<p align="center">
  Built with ❤️ using FastAPI, Next.js, and Qwen3-Embedding
</p>
