# ERR — Ephemeral RAG Reader

Privacy-first, session-based document Q&A webapp (in-memory only) with hybrid retrieval.

## Requirements

- Node.js >= 20.9 (Next.js 16 requirement)
- Docker + Docker Compose (optional, for containerized dev)

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

## Run with Docker (dev)

This repo includes a dev-focused `docker-compose.yml` that starts both services with hot reload:

1) Ensure `backend/.env` exists and contains a valid `OPENROUTER_API_KEY` (and any model overrides you want).

2) Start the stack:

```bash
docker compose up --build
```

3) Open `http://localhost:3000`.

Notes:
- The frontend is configured (in Compose) with `NEXT_PUBLIC_BACKEND_URL=/backend` and Next.js rewrites proxy `/backend/*` to the backend container, so browser requests work without CORS issues.
- Backend runs on `http://localhost:8000` and supports direct access too (e.g. `GET /health`).
- If you are on a network that cannot reach Docker Hub (`auth.docker.io` errors), the Dockerfiles default to pulling base images via `docker.m.daocloud.io` (a Docker Hub mirror). You can override by editing the `ARG *_BASE_IMAGE` in the Dockerfiles.

## Run with Docker (prod-like)

This repo also includes `docker-compose.prod.yml` for a production-like local run:
- Frontend uses `next build` + `next start` (no hot reload)
- Backend uses `uvicorn` (no reload). Note: multiple workers break ERR's in-memory session model unless you add a shared session store or sticky sessions.

```bash
docker compose -f docker-compose.prod.yml up --build
```

Open `http://localhost:3000`.
