from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "http://localhost:3000"
    openrouter_x_title: str = "ERR-App"

    chat_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "qwen/qwen3-embedding-8b"
    embedding_dim: int = 2048

    # Sessions
    session_ttl_seconds: int = 60 * 30  # 30 minutes inactivity
    session_cleanup_interval_seconds: int = 30

    # Chat limits (approximate; we estimate tokens)
    chat_model_context_limit_tokens: int = 32768


def load_settings() -> Settings:
    """
    Lightweight env loader without extra dependency.
    """

    import os

    def getenv_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000"),
        openrouter_x_title=os.getenv("OPENROUTER_X_TITLE", "ERR-App"),
        chat_model=os.getenv("OPENROUTER_CHAT_MODEL", "google/gemini-2.5-flash"),
        embedding_model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b"),
        embedding_dim=getenv_int("OPENROUTER_EMBEDDING_DIM", 2048),
        session_ttl_seconds=getenv_int("ERR_SESSION_TTL_SECONDS", 60 * 30),
        session_cleanup_interval_seconds=getenv_int(
            "ERR_SESSION_CLEANUP_INTERVAL_SECONDS", 30
        ),
        chat_model_context_limit_tokens=getenv_int(
            "ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS", 32768
        ),
    )

