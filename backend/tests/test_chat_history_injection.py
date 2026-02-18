"""Tests for chat history message injection in run_chat.

Verifies that prior conversation turns are injected as proper user/assistant
message pairs rather than collapsed into a single assistant message.

The bug this guards against: when history was injected as one assistant message,
the LLM (temperature=0) would reuse the previous answer verbatim for a different
question, producing identical answers for distinct queries.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from backend.app.chat_pipeline import ChatRequest, run_chat
from backend.app.models.chunk import ChunkModel
from backend.app.openrouter_client import ChatMessage
from backend.app.session_store import SESSIONS, ChatTurn, SessionState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(cid: str, content: str = "some content") -> ChunkModel:
    return ChunkModel(id=cid, content=content, rich_content=content)


def _make_settings(**overrides) -> SimpleNamespace:
    defaults = dict(
        session_ttl_seconds=600,
        chat_history_max_turns=10,
        chat_history_max_chars=20_000,
        chat_model_context_limit_tokens=100_000,
        chat_model_simple="test-model",
        chat_model_complex="test-model",
        embedding_model="test-embed",
        embedding_query_use_instruction=True,
        embedding_query_include_raw=True,
        embedding_query_instruction_template="Instruct: {task}\nQuery: {query}",
        embedding_query_task=(
            "Given a question, retrieve relevant passages from the document that explicitly contain the answer."
        ),
        embedding_aggregation_decay=0.7,
        fast_mode_embedding_aggregation_decay=0.7,
        fast_mode_include_raw_query=False,
        fast_mode_include_neighbors=False,
        fast_mode_candidate_k=20,
        embedding_dim_fast_mode=1024,
        query_fusion_enabled=True,
        query_variants_count=6,
        hyde_enabled=True,
        hyde_max_words=140,
        hyde_drift_sim_threshold=0.5,
        drift_filter_enabled=False,
        drift_sim_threshold=0.5,
        query_variants_max=8,
        fusion_per_query_top_k=20,
        fusion_max_candidates=30,
        rrf_k=60,
        retrieval_parallelism=4,
        llm_rerank_enabled=False,
        llm_rerank_candidate_pool=30,
        llm_rerank_model=None,
        llm_rerank_max_chars=400,
        answer_repeat_guard_enabled=True,
        answer_repeat_answer_similarity_min=0.9,
        answer_repeat_query_similarity_max=0.6,
        repack_strategy="reverse",
        context_include_neighbors=False,
        fast_mode_language_alignment=False,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _FakeRetriever:
    """Minimal retriever stub that returns a fixed chunk list."""

    doc_language = "en"

    def __init__(self, chunks: list[ChunkModel]) -> None:
        self._chunks = chunks

    def search(self, **_kwargs):
        from backend.app.retrieval.hybrid_retriever import ScoredChunk
        return [
            ScoredChunk(
                chunk=c,
                final_score=1.0,
                vector_score=1.0,
                bm25_score_norm=0.0,
            )
            for c in self._chunks
        ]


def _make_session(session_id: str, history: list[ChatTurn] | None = None) -> SessionState:
    s = SessionState(session_id=session_id)
    s.ingest_status = "ready"
    s.doc_language = "en"
    s.retriever = _FakeRetriever([_make_chunk("c1", "The sky is blue.")])
    if history:
        s.chat_history = list(history)
    SESSIONS[session_id] = s
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestChatHistoryInjection(unittest.IsolatedAsyncioTestCase):
    """Verifies that history turns are injected as proper role-alternating messages."""

    def setUp(self) -> None:
        SESSIONS.clear()

    def tearDown(self) -> None:
        SESSIONS.clear()

    async def _run_and_capture_messages(
        self,
        session_id: str,
        query: str,
        answer: str = "Answer [1]",
    ) -> list[ChatMessage]:
        """Run run_chat and return the messages list passed to chat_completion."""
        captured: list[list[ChatMessage]] = []

        async def fake_embeddings(*, model: str, inputs: list[str]):
            n = len(inputs)
            vecs = np.random.default_rng(0).random((n, 4096)).astype(np.float32)
            # L2-normalise so cosine == dot product (matches pipeline invariant)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-9)

        async def fake_chat_completion(*, model, messages, temperature=0.0, **_kw):
            captured.append(list(messages))
            return answer

        async def fake_variants(*, query, doc_language, n):
            return [f"{query}-v{i}" for i in range(1, 3)]

        async def fake_hyde(*, query, doc_language, max_words):
            return f"hyde-{query}"

        async def fake_translate(*, query, doc_language):
            return query

        openrouter = SimpleNamespace(
            embeddings=fake_embeddings,
            chat_completion=fake_chat_completion,
            generate_query_variants=fake_variants,
            generate_hyde_passage=fake_hyde,
            translate_query_for_doc_language=fake_translate,
        )

        settings = _make_settings()
        req = ChatRequest(session_id=session_id, message=query, fast_mode=False, top_k=5)
        await run_chat(req=req, settings=settings, openrouter=openrouter)
        return captured[0]

    async def test_no_history_no_extra_assistant_message(self) -> None:
        """With empty history, messages should be: system + user(CONTEXT+question)."""
        _make_session("s1")
        messages = await self._run_and_capture_messages("s1", "What colour is the sky?")

        roles = [m.role for m in messages]
        self.assertEqual(roles[0], "system")
        self.assertEqual(roles[-1], "user")
        # No stray assistant message before the final user turn
        self.assertNotIn("assistant", roles[:-1])

    async def test_history_injected_as_alternating_turns(self) -> None:
        """With prior history, turns must appear as real user/assistant pairs."""
        history = [
            ChatTurn(role="user", content="First question"),
            ChatTurn(role="assistant", content="First answer [1]"),
        ]
        _make_session("s2", history=history)
        messages = await self._run_and_capture_messages("s2", "Second question")

        roles = [m.role for m in messages]
        # Expected: system, user(hist), assistant(hist), user(current)
        self.assertEqual(roles, ["system", "user", "assistant", "user"])

    async def test_history_content_matches_stored_turns(self) -> None:
        """History message content must match what was stored in session."""
        history = [
            ChatTurn(role="user", content="What is X?"),
            ChatTurn(role="assistant", content="X is Y [1]"),
        ]
        _make_session("s3", history=history)
        messages = await self._run_and_capture_messages("s3", "What is Z?")

        # messages[1] and messages[2] are the history turns
        self.assertEqual(messages[1].role, "user")
        self.assertEqual(messages[1].content, "What is X?")
        self.assertEqual(messages[2].role, "assistant")
        self.assertEqual(messages[2].content, "X is Y [1]")

    async def test_no_collapsed_chat_history_prefix(self) -> None:
        """No message should contain the old 'CHAT_HISTORY:' prefix."""
        history = [
            ChatTurn(role="user", content="q1"),
            ChatTurn(role="assistant", content="a1 [1]"),
        ]
        _make_session("s4", history=history)
        messages = await self._run_and_capture_messages("s4", "q2")

        for msg in messages:
            self.assertNotIn("CHAT_HISTORY:", msg.content)

    async def test_context_in_final_user_message(self) -> None:
        """CONTEXT must be embedded in the final user message, not a separate assistant turn."""
        _make_session("s5")
        messages = await self._run_and_capture_messages("s5", "What colour is the sky?")

        final = messages[-1]
        self.assertEqual(final.role, "user")
        self.assertIn("CONTEXT:", final.content)

    async def test_two_different_questions_get_different_context_messages(self) -> None:
        """Regression: second question must not reuse first answer as its context."""
        _make_session("s6")
        settings = _make_settings()

        captured: list[list[ChatMessage]] = []
        call_count = 0

        async def fake_embeddings(*, model, inputs):
            n = len(inputs)
            rng = np.random.default_rng(call_count)
            vecs = rng.random((n, 4096)).astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-9)

        async def fake_chat_completion(*, model, messages, temperature=0.0, **_kw):
            nonlocal call_count
            captured.append(list(messages))
            call_count += 1
            return f"Answer for call {call_count} [1]"

        async def fake_variants(*, query, doc_language, n):
            return [f"{query}-v1"]

        async def fake_hyde(*, query, doc_language, max_words):
            return f"hyde-{query}"

        async def fake_translate(*, query, doc_language):
            return query

        openrouter = SimpleNamespace(
            embeddings=fake_embeddings,
            chat_completion=fake_chat_completion,
            generate_query_variants=fake_variants,
            generate_hyde_passage=fake_hyde,
            translate_query_for_doc_language=fake_translate,
        )

        req1 = ChatRequest(session_id="s6", message="Question A", fast_mode=False, top_k=5)
        await run_chat(req=req1, settings=settings, openrouter=openrouter)

        req2 = ChatRequest(session_id="s6", message="Question B", fast_mode=False, top_k=5)
        await run_chat(req=req2, settings=settings, openrouter=openrouter)

        self.assertEqual(len(captured), 2)

        # The second call's final user message must contain "Question B", not "Question A"
        second_call_messages = captured[1]
        final_user_msg = second_call_messages[-1]
        self.assertEqual(final_user_msg.role, "user")
        self.assertIn("Question B", final_user_msg.content)
        self.assertNotIn("Question A", final_user_msg.content)

        # The first answer must NOT appear as a standalone assistant message
        # that could be mistaken for the answer to Question B.
        # It should only appear as a proper history turn (role=assistant, exact content).
        # The first answer may appear in history, but must NOT be the last assistant message
        # (which would mean it's being presented as the current answer context).
        last_assistant = next(
            (m for m in reversed(second_call_messages) if m.role == "assistant"), None
        )
        if last_assistant is not None:
            # Last assistant message should be the history turn, not a CONTEXT block
            self.assertNotIn("CONTEXT:", last_assistant.content)

    async def test_retries_when_answer_repeats_previous_turn(self) -> None:
        """If answer repeats previous assistant turn for a new question, retry once."""
        history = [
            ChatTurn(role="user", content="书中对于亚洲人有什么描述？"),
            ChatTurn(role="assistant", content="关于亚洲人，文档中有以下描述 [1]"),
        ]
        _make_session("s7", history=history)

        async def fake_embeddings(*, model, inputs):
            n = len(inputs)
            vecs = np.random.default_rng(42).random((n, 4096)).astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-9)

        answers = [
            "关于亚洲人，文档中有以下描述 [1]",
            "Guyland 的年龄范围是 15 到 24 岁 [1]",
        ]
        captured: list[list[ChatMessage]] = []

        async def fake_chat_completion(*, model, messages, temperature=0.0, **_kw):
            captured.append(list(messages))
            return answers[min(len(captured) - 1, len(answers) - 1)]

        async def fake_variants(*, query, doc_language, n):
            return [f"{query}-v1"]

        async def fake_hyde(*, query, doc_language, max_words):
            return f"hyde-{query}"

        async def fake_translate(*, query, doc_language):
            return query

        openrouter = SimpleNamespace(
            embeddings=fake_embeddings,
            chat_completion=fake_chat_completion,
            generate_query_variants=fake_variants,
            generate_hyde_passage=fake_hyde,
            translate_query_for_doc_language=fake_translate,
        )

        req = ChatRequest(session_id="s7", message="书中 guyland 里边人的平均年龄。", fast_mode=False, top_k=5)
        resp = await run_chat(req=req, settings=_make_settings(), openrouter=openrouter)

        self.assertEqual(len(captured), 2)
        self.assertEqual(resp.answer, "Guyland 的年龄范围是 15 到 24 岁 [1]")


if __name__ == "__main__":
    unittest.main()
