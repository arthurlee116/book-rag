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
    embedding_dim: int = 4096
    embedding_query_use_instruction: bool = True
    embedding_query_include_raw: bool = True
    embedding_query_instruction_template: str = "Instruct: {task}\nQuery:{query}"
    embedding_query_task: str = (
        "Given a question, retrieve relevant passages from the document that explicitly contain the answer."
    )

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
    from pathlib import Path

    def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            return None
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].lstrip()
        if "=" not in stripped:
            return None
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            return None

        # Remove surrounding single or double quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        return key, value

    def _load_dotenv_file(path: Path) -> None:
        """
        Best-effort .env reader. Only sets variables not already in os.environ.
        """
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return
        for raw_line in content.splitlines():
            parsed = _parse_dotenv_line(raw_line)
            if parsed is None:
                continue
            key, value = parsed
            os.environ.setdefault(key, value)

    def _try_load_dotenv() -> None:
        # Optional explicit override, useful in tests / deployments.
        explicit = (os.getenv("ENV_FILE") or "").strip()
        candidates: list[Path] = []
        if explicit:
            candidates.append(Path(explicit))

        # Typical dev usage from repo root: `backend/.env`
        candidates.append(Path("backend/.env"))

        # Also support running from within `backend/`
        candidates.append(Path(".env"))

        for candidate in candidates:
            if candidate.is_file():
                _load_dotenv_file(candidate)
                break

    _try_load_dotenv()

    def getenv_int(name: str, default: int) -> int:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def getenv_bool(name: str, default: bool) -> bool:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

    return Settings(
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        openrouter_http_referer=os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:3000"),
        openrouter_x_title=os.getenv("OPENROUTER_X_TITLE", "ERR-App"),
        chat_model=os.getenv("OPENROUTER_CHAT_MODEL", "google/gemini-2.5-flash"),
        embedding_model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b"),
        embedding_dim=getenv_int("OPENROUTER_EMBEDDING_DIM", 4096),
        embedding_query_use_instruction=getenv_bool(
            "ERR_EMBEDDING_QUERY_USE_INSTRUCTION", True
        ),
        embedding_query_include_raw=getenv_bool("ERR_EMBEDDING_QUERY_INCLUDE_RAW", True),
        embedding_query_instruction_template=os.getenv(
            "ERR_EMBEDDING_QUERY_INSTRUCTION_TEMPLATE",
            "Instruct: {task}\nQuery:{query}",
        ),
        embedding_query_task=os.getenv(
            "ERR_EMBEDDING_QUERY_TASK",
            "Given a question, retrieve relevant passages from the document that explicitly contain the answer.",
        ),
        session_ttl_seconds=getenv_int("ERR_SESSION_TTL_SECONDS", 60 * 30),
        session_cleanup_interval_seconds=getenv_int(
            "ERR_SESSION_CLEANUP_INTERVAL_SECONDS", 30
        ),
        chat_model_context_limit_tokens=getenv_int(
            "ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS", 32768
        ),
    )
