import os
import unittest
from unittest.mock import patch

from backend.app.config import Settings
from backend.app.ingestion.file_parser import ParsedBlock
from backend.app.ingestion_pipeline import ingest_file
from backend.app.session_store import SESSIONS, get_or_create_session


class _DummyOpenRouter:
    async def embeddings(self, *, model: str, inputs: list[str]):
        del model, inputs
        raise AssertionError("embeddings should not be called when chunking fails")


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
                openrouter=_DummyOpenRouter(),
            )

        session = SESSIONS[session_id]
        self.assertEqual(session.ingest_status, "error")
        self.assertIsNotNone(session.ingest_error)
        self.assertIn("boom", session.ingest_error or "")


if __name__ == "__main__":
    unittest.main()
