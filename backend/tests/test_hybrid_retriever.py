import unittest
import numpy as np
from backend.app.retrieval.hybrid_retriever import HybridRetriever
from backend.app.models.chunk import ChunkModel

class TestHybridRetriever(unittest.TestCase):
    def setUp(self):
        # Create dummy data
        self.dim = 8
        self.chunks = [
            ChunkModel(id=f"c{i}", content=f"chunk number {i}", rich_content="", metadata={})
            for i in range(100)
        ]
        # Random embeddings
        rng = np.random.default_rng(42)
        self.embeddings = rng.random((100, self.dim)).astype(np.float32)

        # Initialize retriever
        self.retriever = HybridRetriever(
            embedding_dim=self.dim,
            vector_weight=0.5,
            bm25_weight=0.5,
            candidate_k=10 # Small k to force fallback
        )
        self.retriever.build(chunks=self.chunks, embeddings=self.embeddings, doc_language="en")

    def test_search_correctness(self):
        query_emb = np.random.random((1, self.dim)).astype(np.float32)

        # Run search
        results = self.retriever.search(
            query="chunk",
            query_embedding=query_emb,
            top_k=5
        )

        self.assertEqual(len(results), 5)
        # Verify scores are sorted
        scores = [r.final_score for r in results]
        self.assertTrue(all(scores[i] >= scores[i+1] for i in range(len(scores)-1)))

    def test_search_missing_vector_candidates(self):
        # To test the fallback logic, we need candidates that are found by BM25
        # but NOT by vector search (i.e. not in top candidate_k of vector search).

        # Construct a query that matches a specific chunk text (high BM25)
        # but has an embedding orthogonal to it (low vector score).

        target_idx = 50
        target_chunk = self.chunks[target_idx]

        # Query that strongly matches the text
        query_text = target_chunk.content

        # Embedding that is far from the target chunk's embedding
        # Just use a random one, unlikely to be close.
        query_emb = np.random.random((1, self.dim)).astype(np.float32)

        # We want target_idx to NOT be in the top 10 (candidate_k) of vector search
        # but BE in the top of BM25.

        # Let's verify if it hits the fallback path by inspecting internals or
        # just trusting that with random embeddings and exact text match,
        # it's likely to be a "high BM25, low Vector" candidate.

        results = self.retriever.search(
            query=query_text,
            query_embedding=query_emb,
            top_k=20
        )

        # Check if target is in results
        found = any(r.chunk.id == target_chunk.id for r in results)
        self.assertTrue(found, "Target chunk should be found due to high BM25 score")

        # The correctness check is mostly that it doesn't crash and returns valid scores.
        for r in results:
            self.assertTrue(0.0 <= r.vector_score <= 1.0)
            self.assertTrue(0.0 <= r.bm25_score_norm <= 1.0)

    def test_search_mrl(self):
        query_emb = np.random.random((1, self.dim)).astype(np.float32)
        results = self.retriever.search(
            query="chunk",
            query_embedding=query_emb,
            top_k=5,
            search_dim=4 # Half dimension
        )
        self.assertEqual(len(results), 5)

if __name__ == '__main__':
    unittest.main()
