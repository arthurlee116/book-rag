"""Tests for the clear-chat-context feature.

Covers:
- SessionState.clear_chat_data() method behaviour
- POST /clear/{session_id} endpoint (200 and 404 responses)

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
"""

import os
import unittest

from fastapi.testclient import TestClient

from backend.app.models.chunk import ChunkModel
from backend.app.retrieval.evaluation import EvaluationRecord
from backend.app.session_store import (
    SESSIONS,
    ChatTurn,
    SessionState,
    get_or_create_session,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(cid: str = "c1", content: str = "hello") -> ChunkModel:
    return ChunkModel(id=cid, content=content, rich_content=content)


def _make_evaluation(session_id: str = "s1") -> EvaluationRecord:
    return EvaluationRecord(
        session_id=session_id,
        user_query="test?",
        mode="normal",
        timestamp="2025-01-01T00:00:00",
    )


# ---------------------------------------------------------------------------
# Unit tests for SessionState.clear_chat_data
# ---------------------------------------------------------------------------

class TestClearChatData(unittest.IsolatedAsyncioTestCase):
    """Validates Requirements 3.1, 3.2, 3.3, 3.4."""

    async def test_clears_chat_history(self) -> None:
        session = SessionState(session_id="s1")
        session.chat_history = [
            ChatTurn(role="user", content="hi"),
            ChatTurn(role="assistant", content="hello"),
        ]
        await session.clear_chat_data()
        self.assertEqual(session.chat_history, [])

    async def test_clears_latest_evaluation(self) -> None:
        session = SessionState(session_id="s1")
        session.latest_evaluation = _make_evaluation()
        await session.clear_chat_data()
        self.assertIsNone(session.latest_evaluation)

    async def test_clears_reference_ids_and_references(self) -> None:
        session = SessionState(session_id="s1")
        chunk = _make_chunk()
        session.reference_ids = {"c1": 1}
        session.references = [chunk]
        await session.clear_chat_data()
        self.assertEqual(session.reference_ids, {})
        self.assertEqual(session.references, [])

    async def test_preserves_chunks(self) -> None:
        session = SessionState(session_id="s1")
        chunks = [_make_chunk("c1"), _make_chunk("c2")]
        session.chunks = chunks
        session.chat_history = [ChatTurn(role="user", content="q")]
        await session.clear_chat_data()
        self.assertEqual(session.chunks, chunks)

    async def test_preserves_retriever(self) -> None:
        session = SessionState(session_id="s1")
        sentinel = object()
        session.retriever = sentinel  # type: ignore[assignment]
        await session.clear_chat_data()
        self.assertIs(session.retriever, sentinel)

    async def test_preserves_filename_and_doc_language(self) -> None:
        session = SessionState(session_id="s1")
        session.filename = "book.epub"
        session.doc_language = "zh"
        session.chat_history = [ChatTurn(role="user", content="q")]
        await session.clear_chat_data()
        self.assertEqual(session.filename, "book.epub")
        self.assertEqual(session.doc_language, "zh")

    async def test_noop_on_empty_session(self) -> None:
        """Clearing an already-empty session should succeed without error."""
        session = SessionState(session_id="s1")
        await session.clear_chat_data()
        self.assertEqual(session.chat_history, [])
        self.assertIsNone(session.latest_evaluation)
        self.assertEqual(session.reference_ids, {})
        self.assertEqual(session.references, [])


# ---------------------------------------------------------------------------
# Endpoint tests for POST /clear/{session_id}
# ---------------------------------------------------------------------------

class TestClearChatEndpoint(unittest.TestCase):
    """Validates Requirements 3.5, 3.6."""

    def setUp(self) -> None:
        os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
        SESSIONS.clear()
        from backend.app.main import app
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        SESSIONS.clear()

    def test_returns_200_for_valid_session(self) -> None:
        session = get_or_create_session(session_id="sess-1", ttl_seconds=600)
        session.chat_history = [ChatTurn(role="user", content="hi")]
        session.latest_evaluation = _make_evaluation("sess-1")

        resp = self.client.post("/clear/sess-1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "cleared"})

        # Verify data was actually cleared
        self.assertEqual(session.chat_history, [])
        self.assertIsNone(session.latest_evaluation)

    def test_returns_404_for_unknown_session(self) -> None:
        resp = self.client.post("/clear/nonexistent")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Unknown session", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
