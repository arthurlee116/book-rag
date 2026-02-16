import unittest
from datetime import datetime
from types import SimpleNamespace

from backend.app.chat_pipeline import (
    _decide_language_alignment,
    _align_query_for_retrieval,
    _build_normal_mode_query_expansions,
)
from backend.app.openrouter_client import OpenRouterError
from backend.app.retrieval.evaluation import RetrievalMetrics


class _FakeSession:
    def __init__(self) -> None:
        self.logs: list[str] = []

    async def log(self, message: str) -> None:
        self.logs.append(message)


class _FakeOpenRouter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def translate_query_for_doc_language(self, *, query: str, doc_language: str) -> str:
        self.calls.append("translate")
        return f"{query} ({doc_language})"

    async def generate_query_variants(self, *, query: str, doc_language: str, n: int) -> list[str]:
        self.calls.append("variants")
        return [f"{query}-v1", f"{query}-v2"]

    async def generate_hyde_passage(
        self, *, query: str, doc_language: str, max_words: int
    ) -> str:
        self.calls.append("hyde")
        return f"hyde-{query}-{doc_language}-{max_words}"


class _FailingTranslateOpenRouter(_FakeOpenRouter):
    async def translate_query_for_doc_language(self, *, query: str, doc_language: str) -> str:
        del query, doc_language
        raise OpenRouterError("translate failed", status_code=500)


class TestMainRetrievalHelpers(unittest.IsolatedAsyncioTestCase):
    async def test_decide_language_alignment_skips_same_language(self) -> None:
        settings = SimpleNamespace(
            fast_mode_language_alignment=False,
        )

        should_align, reason = _decide_language_alignment(
            settings=settings,
            user_query="What is this about?",
            doc_language="en",
            fast_mode=False,
        )

        self.assertFalse(should_align)
        self.assertEqual(reason, "already_aligned")

    async def test_align_query_fail_open(self) -> None:
        session = _FakeSession()
        router = _FailingTranslateOpenRouter()
        metrics = RetrievalMetrics(
            session_id="s",
            user_query="hello",
            mode="normal",
            start_time=datetime.now(),
        )

        aligned = await _align_query_for_retrieval(
            session=session,
            openrouter=router,
            user_query="hello",
            doc_language="en",
            should_align=True,
            skip_reason="enabled",
            metrics=metrics,
        )

        self.assertEqual(aligned, "hello")
        self.assertTrue(any("language alignment failed" in log for log in session.logs))
        step = metrics.steps[-1]
        self.assertEqual(step["name"], "language_alignment")
        self.assertTrue(step["skipped"])
        self.assertEqual(step["reason"], "api_error_fallback")

    async def test_hyde_runs_independently_from_query_fusion(self) -> None:
        session = _FakeSession()
        router = _FakeOpenRouter()
        settings = SimpleNamespace(
            query_fusion_enabled=False,
            query_variants_count=6,
            hyde_enabled=True,
            hyde_max_words=140,
        )

        query_texts, hyde_text = await _build_normal_mode_query_expansions(
            session=session,
            openrouter=router,
            settings=settings,
            base_query="base",
            user_query="user",
            doc_language="en",
        )

        self.assertEqual(query_texts, ["base", "user"])
        self.assertTrue(hyde_text.startswith("hyde-base-en-140"))
        self.assertIn("hyde", router.calls)
        self.assertNotIn("variants", router.calls)


if __name__ == "__main__":
    unittest.main()
