from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import numpy as np

from backend.app.chat_pipeline import ChatRequest, run_chat
from backend.app.config import Settings
from backend.app.ingestion.file_parser import ParsedBlock
from backend.app.ingestion_pipeline import ingest_file
from backend.app.models.chunk import ChunkModel
from backend.app.openrouter_client import ChatMessage, OpenRouterClient
from backend.app.retrieval.hybrid_retriever import HybridRetriever, ScoredChunk
from backend.app.session_store import SESSIONS, SessionState, get_or_create_session


def _make_chunk(
    cid: str,
    content: str,
    *,
    prev: str | None = None,
    next_: str | None = None,
) -> ChunkModel:
    return ChunkModel(
        id=cid,
        content=content,
        rich_content=content,
        prev_content=prev,
        next_content=next_,
    )


def _make_chat_settings(**overrides) -> SimpleNamespace:
    defaults = {
        "session_ttl_seconds": 600,
        "chat_history_max_turns": 10,
        "chat_history_max_chars": 20_000,
        "chat_model_context_limit_tokens": 100_000,
        "chat_model_simple": "test-chat",
        "chat_model_complex": "test-chat-complex",
        "embedding_model": "test-embed",
        "embedding_query_use_instruction": True,
        "embedding_query_include_raw": True,
        "embedding_query_instruction_template": "Instruct: {task}\nQuery: {query}",
        "embedding_query_task": (
            "Given a question, retrieve relevant passages from the document that explicitly contain the answer."
        ),
        "embedding_aggregation_decay": 0.7,
        "fast_mode_embedding_aggregation_decay": 0.7,
        "fast_mode_include_raw_query": False,
        "fast_mode_include_neighbors": False,
        "fast_mode_candidate_k": 20,
        "embedding_dim_fast_mode": 1024,
        "query_fusion_enabled": True,
        "query_variants_count": 6,
        "hyde_enabled": True,
        "hyde_max_words": 140,
        "hyde_drift_sim_threshold": 0.5,
        "drift_filter_enabled": True,
        "drift_sim_threshold": 0.5,
        "query_variants_max": 8,
        "fusion_per_query_top_k": 20,
        "fusion_max_candidates": 30,
        "rrf_k": 60,
        "retrieval_parallelism": 4,
        "llm_rerank_enabled": True,
        "llm_rerank_candidate_pool": 30,
        "llm_rerank_model": None,
        "llm_rerank_max_chars": 400,
        "answer_repeat_guard_enabled": True,
        "answer_repeat_answer_similarity_min": 0.9,
        "answer_repeat_query_similarity_max": 0.6,
        "repack_strategy": "reverse",
        "context_include_neighbors": True,
        "fast_mode_language_alignment": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _CapturingRetriever:
    doc_language = "en"

    def __init__(self, chunks: list[ChunkModel]) -> None:
        self._chunks = chunks
        self.calls: list[dict] = []

    def search(self, **kwargs):
        self.calls.append(dict(kwargs))
        top_k = int(kwargs.get("top_k", len(self._chunks)))
        return [
            ScoredChunk(
                chunk=chunk,
                final_score=1.0 - (idx * 0.1),
                vector_score=1.0 - (idx * 0.1),
                bm25_score_norm=0.0,
            )
            for idx, chunk in enumerate(self._chunks[:top_k])
        ]


class _FakeResponse:
    status_code = 200

    def __init__(self, payload) -> None:
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload) -> None:
        self.payload = payload
        self.posts: list[tuple[str, dict | None]] = []

    async def post(self, path: str, json=None):
        self.posts.append((path, json))
        return _FakeResponse(self.payload)


class _WarmupTrackingRetriever:
    last_instance = None

    def __init__(self, **kwargs):
        del kwargs
        self.doc_language = "en"
        self.warmup_calls: list[int | None] = []
        type(self).last_instance = self

    def build(self, *, chunks, embeddings):
        del chunks, embeddings
        return None

    def warmup_mrl(self, search_dim: int | None):
        self.warmup_calls.append(search_dim)
        return None


class TestReviewRegressionFixes(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        SESSIONS.clear()

    def tearDown(self) -> None:
        SESSIONS.clear()

    async def test_openrouter_reuses_persistent_client_and_helper_calls_disable_reasoning(self) -> None:
        client = OpenRouterClient(Settings(openrouter_api_key="test-key"))
        real_client = client._client
        self.assertIsInstance(real_client, httpx.AsyncClient)

        fake_client = _FakeAsyncClient({"choices": [{"message": {"content": "aligned query"}}]})
        client._client = fake_client
        try:
            translated = await client.translate_query_for_doc_language(query="hello", doc_language="en")
            await client.chat_completion(
                model="test-model",
                messages=[ChatMessage(role="user", content="Reply with OK.")],
            )
        finally:
            client._client = real_client
            await client.aclose()

        self.assertEqual(translated, "aligned query")
        self.assertEqual(len(fake_client.posts), 2)
        helper_payload = fake_client.posts[0][1] or {}
        default_payload = fake_client.posts[1][1] or {}
        self.assertNotIn("reasoning", helper_payload)
        self.assertEqual(default_payload["reasoning"], {"max_tokens": 64})

    async def test_fast_mode_run_chat_uses_mrl_search_and_skips_normal_mode_helpers(self) -> None:
        session_id = "fast-mode-session"
        chunk = _make_chunk(
            "c-fast",
            "The answer lives here.",
            prev="Previous chunk should stay out of fast-mode context.",
            next_="Next chunk should stay out of fast-mode context.",
        )
        retriever = _CapturingRetriever([chunk])
        session = SessionState(session_id=session_id)
        session.ingest_status = "ready"
        session.doc_language = "en"
        session.retriever = retriever  # type: ignore[assignment]
        SESSIONS[session_id] = session

        captured_messages: list[list[ChatMessage]] = []

        async def fake_embeddings(*, model, inputs):
            del model
            rng = np.random.default_rng(7)
            vecs = rng.random((len(inputs), 4096)).astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            return vecs / np.maximum(norms, 1e-9)

        async def fake_chat_completion(*, model, messages, temperature=0.0, **_kwargs):
            del model, temperature
            captured_messages.append(list(messages))
            return "Fast answer [1]"

        async def fail_helper(*args, **kwargs):
            del args, kwargs
            raise AssertionError("normal-mode helper should not run in fast mode")

        openrouter = SimpleNamespace(
            embeddings=fake_embeddings,
            chat_completion=fake_chat_completion,
            translate_query_for_doc_language=fail_helper,
            generate_query_variants=fail_helper,
            generate_hyde_passage=fail_helper,
            rerank_passages_yesno=fail_helper,
        )

        req = ChatRequest(session_id=session_id, message="Where is the answer?", fast_mode=True, top_k=5)
        resp = await run_chat(req=req, settings=_make_chat_settings(), openrouter=openrouter)  # type: ignore[arg-type]

        self.assertEqual(resp.answer, "Fast answer [1]")
        self.assertEqual([c["id"] for c in resp.citations], ["c-fast"])
        self.assertEqual(len(retriever.calls), 1)
        search_call = retriever.calls[0]
        self.assertEqual(search_call["search_dim"], 1024)
        self.assertEqual(search_call["candidate_k_override"], 20)
        self.assertEqual(search_call["query"], "Where is the answer?")
        self.assertEqual(search_call["expanded_query"], "Where is the answer?")

        self.assertEqual(len(captured_messages), 1)
        final_user_message = captured_messages[0][-1]
        self.assertEqual(final_user_message.role, "user")
        self.assertNotIn("PREV:", final_user_message.content)
        self.assertNotIn("NEXT:", final_user_message.content)

        assert session.latest_evaluation is not None
        self.assertEqual(session.latest_evaluation.mode, "fast")
        steps = {step.name: step for step in session.latest_evaluation.steps}
        self.assertTrue(steps["drift_filter"].skipped)
        self.assertEqual(steps["drift_filter"].reason, "fast_mode")
        self.assertTrue(steps["llm_rerank"].skipped)
        self.assertEqual(steps["llm_rerank"].reason, "fast_mode")

    async def test_ingestion_prewarms_fast_mode_mrl_index(self) -> None:
        settings = Settings(
            openrouter_api_key="test-key",
            embedding_dim=8,
            embedding_dim_fast_mode=4,
        )
        session_id = "prewarm-session"
        get_or_create_session(session_id=session_id, ttl_seconds=settings.session_ttl_seconds)

        class _EmbeddingStub:
            async def embeddings(self, *, model: str, inputs: list[str]):
                del model
                return np.ones((len(inputs), 8), dtype=np.float32)

        chunk = _make_chunk("c-prewarm", "book content")
        _WarmupTrackingRetriever.last_instance = None

        with (
            patch("backend.app.ingestion_pipeline.HybridRetriever", _WarmupTrackingRetriever),
            patch(
                "backend.app.ingestion_pipeline.FileParser.parse",
                return_value=[ParsedBlock(text="book content", rich_text="book content", metadata={})],
            ),
            patch("backend.app.ingestion_pipeline.Chunker.chunk", return_value=[chunk]),
        ):
            await ingest_file(
                session_id=session_id,
                filename="book.txt",
                content=b"book content",
                settings=settings,
                openrouter=_EmbeddingStub(),  # type: ignore[arg-type]
            )

        retriever = _WarmupTrackingRetriever.last_instance
        self.assertIsNotNone(retriever)
        self.assertEqual(retriever.warmup_calls, [4])


class TestHybridRetrieverBilingual(unittest.TestCase):
    def test_build_auto_detects_chinese_and_bm25_matches_common_phrase(self) -> None:
        chunks = [
            _make_chunk("zh-hit", "这本书讨论平均年龄和成长阶段。"),
            _make_chunk("zh-miss", "这本书讨论学校生活和友情。"),
        ]
        embeddings = np.zeros((2, 8), dtype=np.float32)
        retriever = HybridRetriever(
            embedding_dim=8,
            vector_weight=0.5,
            bm25_weight=0.5,
            candidate_k=2,
        )
        retriever.build(chunks=chunks, embeddings=embeddings)

        results = retriever.search(
            query="平均年龄",
            query_embedding=np.zeros((1, 8), dtype=np.float32),
            top_k=1,
        )

        self.assertEqual(retriever.doc_language, "zh")
        self.assertEqual(results[0].chunk.id, "zh-hit")


if __name__ == "__main__":
    unittest.main()
