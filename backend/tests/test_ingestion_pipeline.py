import asyncio
import os
import unittest
from unittest.mock import patch

from backend.app.config import Settings
from backend.app.ingestion.file_parser import ParsedBlock
from backend.app.ingestion_pipeline import ingest_file
from backend.app.models.chunk import ChunkModel
from backend.app.session_store import SESSIONS, get_or_create_session


class _DummyOpenRouter:
    async def embeddings(self, *, model: str, inputs: list[str]):
        del model, inputs
        raise AssertionError("embeddings should not be called when chunking fails")


class _RaceOpenRouter:
    async def embeddings(self, *, model: str, inputs: list[str]):
        del model
        text = " ".join(inputs).lower()
        if "first" in text:
            await asyncio.sleep(0.2)
        else:
            await asyncio.sleep(0.02)
        import numpy as np

        return np.ones((len(inputs), 8), dtype=np.float32)


class _FakeRetriever:
    def __init__(self, **kwargs):
        del kwargs
        self.doc_language = "en"

    def build(self, *, chunks, embeddings):
        del chunks, embeddings
        return None

    def warmup_mrl(self, search_dim: int | None):
        del search_dim
        return None


class TestIngestionPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_chunking_failure_sets_session_error(self) -> None:
        os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
        SESSIONS.clear()

        settings = Settings(openrouter_api_key="test-key")
        session_id = "chunking-fail-session"
        get_or_create_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)

        with (
            patch(
                "backend.app.ingestion_pipeline.FileParser.parse",
                return_value=[ParsedBlock(text="hello", rich_text="hello", metadata={})],
            ),
            patch("backend.app.ingestion_pipeline.Chunker.chunk", side_effect=RuntimeError("boom")),
        ):
            await ingest_file(
                session_id=session_id,
                filename="x.txt",
                content=b"hello",
                settings=settings,
                openrouter=_DummyOpenRouter(),  # type: ignore[arg-type]
            )

        session = SESSIONS[session_id]
        self.assertEqual(session.ingest_status, "error")
        self.assertIsNotNone(session.ingest_error)
        self.assertIn("boom", session.ingest_error or "")

    async def test_stale_ingestion_result_is_discarded(self) -> None:
        os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
        SESSIONS.clear()

        settings = Settings(
            openrouter_api_key="test-key",
            embedding_dim=8,
            embedding_dim_fast_mode=4,
        )
        session_id = "ingestion-race-session"
        session = get_or_create_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)

        async with session.lock:
            session.ingest_generation = 1

        first_chunk = ChunkModel(
            id="c1",
            content="first document body",
            rich_content="first document body",
        )
        second_chunk = ChunkModel(
            id="c2",
            content="second document body",
            rich_content="second document body",
        )

        with (
            patch("backend.app.ingestion_pipeline.HybridRetriever", _FakeRetriever),
            patch(
                "backend.app.ingestion_pipeline.FileParser.parse",
                side_effect=[
                    [ParsedBlock(text="first", rich_text="first", metadata={})],
                    [ParsedBlock(text="second", rich_text="second", metadata={})],
                ],
            ),
            patch(
                "backend.app.ingestion_pipeline.Chunker.chunk",
                side_effect=[[first_chunk], [second_chunk]],
            ),
        ):
            t1 = asyncio.create_task(
                ingest_file(
                    session_id=session_id,
                    filename="first.txt",
                    content=b"first",
                    settings=settings,
                    openrouter=_RaceOpenRouter(),  # type: ignore[arg-type]
                    ingest_generation=1,
                )
            )
            await asyncio.sleep(0.03)
            async with session.lock:
                session.ingest_generation = 2
            t2 = asyncio.create_task(
                ingest_file(
                    session_id=session_id,
                    filename="second.txt",
                    content=b"second",
                    settings=settings,
                    openrouter=_RaceOpenRouter(),  # type: ignore[arg-type]
                    ingest_generation=2,
                )
            )

            await asyncio.gather(t1, t2)

        self.assertEqual(session.filename, "second.txt")
        self.assertEqual(session.ingest_status, "ready")
        self.assertEqual([c.id for c in session.chunks], ["c2"])


if __name__ == "__main__":
    unittest.main()
