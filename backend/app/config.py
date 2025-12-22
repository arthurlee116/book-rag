from __future__ import annotations

from pydantic import BaseModel


class Settings(BaseModel):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_http_referer: str = "http://localhost:3000"
    openrouter_x_title: str = "ERR-App"

    chat_model: str = "google/gemini-2.5-flash"  # deprecated, use simple/complex
    chat_model_simple: str = "google/gemini-2.5-flash-lite-preview-09-2025"
    chat_model_complex: str = "google/gemini-2.5-flash-preview-09-2025"
    embedding_model: str = "qwen/qwen3-embedding-8b"
    embedding_dim: int = 4096
    embedding_dim_fast_mode: int = 1024  # MRL: use lower dimension in fast mode for speed
    embedding_query_use_instruction: bool = True
    embedding_query_include_raw: bool = True
    embedding_query_instruction_template: str = "Instruct: {task}\nQuery:{query}"
    embedding_query_task: str = (
        "Given a question, retrieve relevant passages from the document that explicitly contain the answer."
    )

    # Chunking
    chunk_target_tokens: int = 6144
    chunk_overlap_tokens: int = 600
    semantic_chunking_enabled: bool = True
    semantic_chunking_threshold: float = 0.5

    # Re-packing strategy: "forward" (default order), "reverse" (most relevant at end)
    repack_strategy: str = "reverse"

    # Query embedding aggregation decay factor (0.7 means each subsequent embedding has 0.7x weight)
    embedding_aggregation_decay: float = 0.7

    # Retrieval (recall-oriented)
    query_fusion_enabled: bool = True
    query_variants_count: int = 6
    query_variants_max: int = 8
    hyde_enabled: bool = True
    hyde_max_words: int = 140

    # Query drift filtering
    drift_filter_enabled: bool = True
    drift_sim_threshold: float = 0.8
    hyde_drift_sim_threshold: float = 0.6

    # Fusion parameters
    rrf_k: int = 60
    fusion_per_query_top_k: int = 50
    fusion_max_candidates: int = 120

    # LLM rerank (yes/no judge using chat model)
    llm_rerank_enabled: bool = True
    llm_rerank_model: str = ""  # default: use chat_model
    llm_rerank_candidate_pool: int = 30
    llm_rerank_max_chars: int = 900

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

    def getenv_float(name: str, default: float) -> float:
        raw = os.getenv(name)
        if raw is None or raw.strip() == "":
            return default
        try:
            return float(raw)
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
        chat_model_simple=os.getenv("OPENROUTER_CHAT_MODEL_SIMPLE", "google/gemini-2.5-flash-lite-preview-09-2025"),
        chat_model_complex=os.getenv("OPENROUTER_CHAT_MODEL_COMPLEX", "google/gemini-2.5-flash-preview-09-2025"),
        embedding_model=os.getenv("OPENROUTER_EMBEDDING_MODEL", "qwen/qwen3-embedding-8b"),
        embedding_dim=getenv_int("OPENROUTER_EMBEDDING_DIM", 4096),
        embedding_dim_fast_mode=getenv_int("ERR_EMBEDDING_DIM_FAST_MODE", 1024),
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
        # Chunking params - keep small for low-memory servers (2G)
        chunk_target_tokens=512,
        chunk_overlap_tokens=50,
        semantic_chunking_enabled=True,
        semantic_chunking_threshold=0.5,
        repack_strategy=os.getenv("ERR_REPACK_STRATEGY", "reverse"),
        embedding_aggregation_decay=getenv_float("ERR_EMBEDDING_AGGREGATION_DECAY", 0.7),
        query_fusion_enabled=getenv_bool("ERR_QUERY_FUSION_ENABLED", True),
        query_variants_count=getenv_int("ERR_QUERY_VARIANTS_COUNT", 6),
        query_variants_max=getenv_int("ERR_QUERY_VARIANTS_MAX", 8),
        hyde_enabled=getenv_bool("ERR_HYDE_ENABLED", True),
        hyde_max_words=getenv_int("ERR_HYDE_MAX_WORDS", 140),
        drift_filter_enabled=getenv_bool("ERR_DRIFT_FILTER_ENABLED", True),
        drift_sim_threshold=getenv_float("ERR_DRIFT_SIM_THRESHOLD", 0.25),
        hyde_drift_sim_threshold=getenv_float("ERR_HYDE_DRIFT_SIM_THRESHOLD", 0.15),
        rrf_k=getenv_int("ERR_RRF_K", 60),
        fusion_per_query_top_k=getenv_int("ERR_FUSION_PER_QUERY_TOP_K", 50),
        fusion_max_candidates=getenv_int("ERR_FUSION_MAX_CANDIDATES", 120),
        llm_rerank_enabled=getenv_bool("ERR_LLM_RERANK_ENABLED", True),
        llm_rerank_model=os.getenv("ERR_LLM_RERANK_MODEL", ""),
        llm_rerank_candidate_pool=getenv_int("ERR_LLM_RERANK_CANDIDATE_POOL", 30),
        llm_rerank_max_chars=getenv_int("ERR_LLM_RERANK_MAX_CHARS", 900),
        session_ttl_seconds=getenv_int("ERR_SESSION_TTL_SECONDS", 60 * 30),
        session_cleanup_interval_seconds=getenv_int(
            "ERR_SESSION_CLEANUP_INTERVAL_SECONDS", 30
        ),
        chat_model_context_limit_tokens=getenv_int(
            "ERR_CHAT_MODEL_CONTEXT_LIMIT_TOKENS", 32768
        ),
    )
