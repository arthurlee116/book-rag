from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, load_settings
from .openrouter_client import OpenRouterClient
from .routes import router
from .session_store import cleanup_expired_sessions


async def _cleanup_loop(settings: Settings, shutdown_event: asyncio.Event) -> None:
    while not shutdown_event.is_set():
        cleanup_expired_sessions()
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=settings.session_cleanup_interval_seconds)
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings
    app.state.openrouter = OpenRouterClient(settings)
    shutdown_event = asyncio.Event()
    app.state.shutdown_event = shutdown_event
    cleanup_task = asyncio.create_task(_cleanup_loop(settings, shutdown_event))
    try:
        yield
    finally:
        shutdown_event.set()
        cleanup_task.cancel()
        await app.state.openrouter.aclose()


app = FastAPI(title="ERR Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
