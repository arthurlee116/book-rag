import unittest

from backend.app.ingestion import chunker as chunker_module
from backend.app.ingestion.chunker import Chunker, estimate_tokens
from backend.app.ingestion.file_parser import ParsedBlock


class TestChunker(unittest.TestCase):
    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens("hello world"), 2)
        self.assertEqual(estimate_tokens("你好"), 2)
        self.assertEqual(estimate_tokens("hello 你好"), 3)

    def test_empty_input_returns_empty(self):
        chunker = Chunker(target_tokens=100, overlap_tokens=0, semantic_enabled=False)
        block = ParsedBlock(text="   \n\n   ", rich_text="", metadata={})
        self.assertEqual(chunker.chunk(blocks=[block]), [])

    def test_fixed_chunking_without_semantic(self):
        text = "alpha beta. gamma delta. epsilon zeta. eta theta."
        block = ParsedBlock(text=text, rich_text=text, metadata={})
        chunker = Chunker(target_tokens=4, overlap_tokens=0, semantic_enabled=False)

        chunks = chunker.chunk(blocks=[block])

        self.assertEqual(len(chunks), 2)
        self.assertIn("alpha beta", chunks[0].content)
        self.assertIn("gamma delta", chunks[0].content)
        self.assertIn("epsilon zeta", chunks[1].content)
        self.assertIn("eta theta", chunks[1].content)

    def test_overlap_tokens_applied(self):
        text = "alpha beta. gamma delta. epsilon zeta. eta theta."
        block = ParsedBlock(text=text, rich_text=text, metadata={})
        chunker = Chunker(target_tokens=4, overlap_tokens=2, semantic_enabled=False)

        chunks = chunker.chunk(blocks=[block])

        self.assertEqual(len(chunks), 3)
        self.assertIn("alpha beta", chunks[0].content)
        self.assertIn("gamma delta", chunks[0].content)
        self.assertIn("gamma delta", chunks[1].content)
        self.assertIn("epsilon zeta", chunks[1].content)
        self.assertIn("epsilon zeta", chunks[2].content)
        self.assertIn("eta theta", chunks[2].content)

    def test_semantic_split_with_mocked_distances(self):
        sentence1 = ("cat ") * 30
        sentence2 = ("cat ") * 30
        sentence3 = ("quantum ") * 30
        sentence4 = ("quantum ") * 30
        text = f"{sentence1.strip()}. {sentence2.strip()}. {sentence3.strip()}. {sentence4.strip()}."

        block = ParsedBlock(text=text, rich_text=text, metadata={})
        chunker = Chunker(target_tokens=300, overlap_tokens=0, semantic_enabled=True, semantic_threshold=0.5)
        chunker._calculate_cosine_distances = lambda _sentences: [0.1, 0.9, 0.1]  # type: ignore[method-assign]

        chunks = chunker.chunk(blocks=[block])

        self.assertEqual(len(chunks), 2)
        self.assertIn("cat", chunks[0].content.lower())
        self.assertIn("quantum", chunks[1].content.lower())

    def test_semantic_disabled_when_max_sentences_exceeded(self):
        text = "one two. three four. five six."
        block = ParsedBlock(text=text, rich_text=text, metadata={})
        chunker = Chunker(
            target_tokens=100,
            overlap_tokens=0,
            semantic_enabled=True,
            semantic_threshold=0.5,
            semantic_max_sentences=2,
        )

        def should_not_run(_sentences):
            raise AssertionError("semantic distance should be skipped when sentence limit is exceeded")

        chunker._calculate_cosine_distances = should_not_run  # type: ignore[method-assign]
        chunks = chunker.chunk(blocks=[block])

        self.assertEqual(len(chunks), 1)
        self.assertIn("one two", chunks[0].content)

    def test_semantic_model_retries_across_instances_after_transient_failure(self):
        original_sentence_transformer = chunker_module.SentenceTransformer
        original_shared_model = chunker_module._SHARED_EMBED_MODEL
        original_shared_model_name = chunker_module._SHARED_EMBED_MODEL_NAME

        class DummySentenceTransformer:
            def encode(self, sentences):
                return [[0.0, 0.0] for _ in sentences]

        calls = {"count": 0}

        def flaky_sentence_transformer(_model_name, device="cpu"):
            del device
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient initialization failure")
            return DummySentenceTransformer()

        try:
            chunker_module.SentenceTransformer = flaky_sentence_transformer  # type: ignore[assignment]
            chunker_module._SHARED_EMBED_MODEL = None
            chunker_module._SHARED_EMBED_MODEL_NAME = None

            first = Chunker(semantic_enabled=True)
            first._ensure_embed_model()
            self.assertTrue(first._embed_model_failed)
            self.assertIsNone(first._embed_model)

            second = Chunker(semantic_enabled=True)
            second._ensure_embed_model()
            self.assertFalse(second._embed_model_failed)
            self.assertIsNotNone(second._embed_model)
            self.assertEqual(calls["count"], 2)
        finally:
            chunker_module.SentenceTransformer = original_sentence_transformer
            chunker_module._SHARED_EMBED_MODEL = original_shared_model
            chunker_module._SHARED_EMBED_MODEL_NAME = original_shared_model_name


if __name__ == "__main__":
    unittest.main()
