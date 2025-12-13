# ERR — Ephemeral RAG Reader

Privacy-first, session-based document Q&A webapp (in-memory only) with hybrid retrieval.

## Requirements

- Node.js >= 20.9 (Next.js 16 requirement)

## Run backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# edit backend/.env and set OPENROUTER_API_KEY

uvicorn backend.app.main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000`.
