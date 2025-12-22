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

<p align="center">
  <strong>English</strong> | <a href="README.zh-CN.md">简体中文</a>
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
| 📊 **Retrieval Evaluation** | Inspect each retrieval pipeline step (BM25, vector search, fusion, rerank) with detailed metrics |

## 🏗️ Architecture

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

- **Git** — Version control
- **Python 3.11+** — Backend runtime
- **Node.js 18+** — Frontend runtime
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

uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install --legacy-peer-deps
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) 🎉

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
│   │   ├── ingestion/           # Document parsing & chunking
│   │   └── retrieval/           # FAISS + BM25 hybrid search, evaluation metrics
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # React components (Ant Design)
│   │   ├── lib/                 # Zustand state & types
│   │   ├── App.tsx              # Main app component
│   │   ├── main.tsx             # Entry point
│   │   ├── theme.ts             # Ant Design dark theme
│   │   └── index.less           # Global styles
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
├── docker-compose.yml
└── docker-compose.prod.yml
```

## ⚙️ Configuration

Backend settings in `backend/.env`:

```bash
OPENROUTER_API_KEY=your_key_here
OPENROUTER_CHAT_MODEL_SIMPLE=google/gemini-2.5-flash-lite-preview-09-2025
OPENROUTER_CHAT_MODEL_COMPLEX=google/gemini-2.5-flash-preview-09-2025
OPENROUTER_EMBEDDING_MODEL=qwen/qwen3-embedding-8b
```

Frontend settings in `frontend/.env.local`:

```bash
VITE_BACKEND_URL=http://localhost:8000
```

## 🧪 Testing

```bash
# Backend unit tests
cd backend && python -m unittest discover -s tests -p "test_*.py"

# Frontend lint
cd frontend && npm run lint
```

## 🚀 Production Deployment

### Server Info

- **Domain**: https://bookembed.net
- **Server**: Tencent Cloud (Hong Kong)
- **IP**: 43.159.200.246
- **OS**: Ubuntu 24.04
- **User**: ubuntu

### Deployment Steps

1. **SSH to server and clone repo**:
```bash
ssh ubuntu@43.159.200.246
cd ~ && git clone https://github.com/arthurlee116/book-rag.git
```

2. **Copy `.env` file** (from local machine):
```bash
scp backend/.env ubuntu@43.159.200.246:~/book-rag/backend/.env
```

3. **Fix `docker-compose.prod.yml`** (remove frontend command override):
```bash
cd ~/book-rag
# Remove the "command:" section under frontend service
# The Dockerfile.prod CMD should be used instead
```

4. **Start services**:
```bash
cd ~/book-rag
sudo docker compose -f docker-compose.prod.yml up -d --build
```

5. **Verify**:
```bash
sudo docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health
curl http://localhost:3000
```

### Caddy Configuration

Caddy is used as reverse proxy with automatic HTTPS (Let's Encrypt).

**Install Caddy** (Ubuntu):
```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

**Caddyfile** (`/etc/caddy/Caddyfile`):
```
bookembed.net {
    handle /backend/* {
        uri strip_prefix /backend
        reverse_proxy localhost:8000
    }

    # PERF: cache fingerprinted static assets aggressively (repeat-visit speed).
    # Without this, Lighthouse/PageSpeed reports "Use efficient cache lifetimes"
    # with TTL=0 for `/assets/*`.
    handle /assets/* {
        header Cache-Control "public, max-age=31536000, immutable"
        reverse_proxy localhost:3000
    }

    # SPA entry (and any non-asset route): avoid caching HTML so deployments take effect quickly.
    handle {
        header Cache-Control "no-cache"
        reverse_proxy localhost:3000
    }
}
```

**Restart Caddy**:
```bash
sudo systemctl restart caddy
```

### Useful Commands

```bash
# View logs
sudo docker compose -f ~/book-rag/docker-compose.prod.yml logs -f

# Restart services
sudo docker compose -f ~/book-rag/docker-compose.prod.yml restart

# Update and redeploy
cd ~/book-rag && git pull && sudo docker compose -f docker-compose.prod.yml up -d --build

# Check Caddy status
sudo systemctl status caddy
```

### CI/CD Automatic Deployment

The project uses GitHub Actions for automatic deployment. Every push to `main` branch triggers:

1. SSH to server and pull latest code
2. Rebuild and restart Docker containers
3. Health check on both frontend and backend

**Workflow file**: `.github/workflows/deploy.yml`

**Required GitHub Secrets**:
| Secret | Description |
|--------|-------------|
| `DEPLOY_HOST` | Server IP address |
| `DEPLOY_USER` | SSH username |
| `DEPLOY_SSH_KEY` | SSH private key for deployment |

**Manual trigger**: You can also manually trigger deployment from the Actions tab.

## 📄 License

[Apache 2.0](LICENSE)

---

<p align="center">
  Built with ❤️ using FastAPI, Vite, React, and Ant Design
</p>
