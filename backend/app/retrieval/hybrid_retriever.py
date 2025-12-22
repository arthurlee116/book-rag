from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional
from .evaluation import RetrievalMetrics

import numpy as np

from ..models.chunk import ChunkModel


try:
    import faiss  # type: ignore
except Exception as e:  # noqa: BLE001
    faiss = None  # type: ignore[assignment]
    _FAISS_IMPORT_ERROR = e
else:
    _FAISS_IMPORT_ERROR = None

try:
    import jieba  # type: ignore
except Exception as e:  # noqa: BLE001
    jieba = None  # type: ignore[assignment]
    _JIEBA_IMPORT_ERROR = e
else:
    _JIEBA_IMPORT_ERROR = None

try:
    import spacy  # type: ignore
except Exception as e:  # noqa: BLE001
    spacy = None  # type: ignore[assignment]
    _SPACY_IMPORT_ERROR = e
else:
    _SPACY_IMPORT_ERROR = None

from rank_bm25 import BM25Okapi  # noqa: E402


Language = Literal["en", "zh"]


def detect_dominant_language(text: str) -> Language:
    # Very small heuristic: if there is meaningful CJK presence, treat as zh.
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "zh" if cjk > max(10, latin) else "en"


def _l2_normalize(vectors: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, eps)
    return vectors / norms


@dataclass(frozen=True)
class ScoredChunk:
    chunk: ChunkModel
    final_score: float
    vector_score: float
    bm25_score_norm: float


class HybridRetriever:
    """
    In-memory hybrid retriever:
    - Vector search via FAISS IndexFlatIP with L2-normalized embeddings (cosine similarity)
    - Keyword search via BM25
    - Per-query MinMax normalization for BM25 scores (top-N for that query)
    - Late fusion:
        final = vector_weight * vector + bm25_weight * bm25_norm
    """

    def __init__(
        self,
        *,
        embedding_dim: int = 2048,
        vector_weight: float = 0.8,
        bm25_weight: float = 0.2,
        candidate_k: int = 50,
    ) -> None:
        if abs((vector_weight + bm25_weight) - 1.0) > 1e-6:
            raise ValueError("vector_weight + bm25_weight must sum to 1.0")
        if candidate_k < 1:
            raise ValueError("candidate_k must be >= 1")

        self.embedding_dim = embedding_dim
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.candidate_k = candidate_k

        self._chunks: list[ChunkModel] = []
        self._doc_embeddings: np.ndarray | None = None
        self._faiss_index = None
        self._bm25: BM25Okapi | None = None
        self._doc_language: Language | None = None

        self._spacy_nlp = None

    @property
    def doc_language(self) -> Language | None:
        return self._doc_language

    def _ensure_spacy(self) -> None:
        if self._spacy_nlp is not None:
            return
        if spacy is None:
            raise RuntimeError(
                f"spacy is required for English tokenization. Import error: {_SPACY_IMPORT_ERROR}"
            )
        # Avoid requiring a downloaded model; blank pipeline is enough for tokenization.
        self._spacy_nlp = spacy.blank("en")

    def _tokenize(self, text: str, *, language: Language) -> list[str]:
        text = text.strip()
        if not text:
            return []

        if language == "zh":
            if jieba is None:
                raise RuntimeError(
                    f"jieba is required for Chinese tokenization. Import error: {_JIEBA_IMPORT_ERROR}"
                )
            tokens = [t.strip() for t in jieba.lcut(text) if t.strip()]
            return tokens

        self._ensure_spacy()
        assert self._spacy_nlp is not None
        doc = self._spacy_nlp(text)
        tokens: list[str] = []
        for t in doc:
            if t.is_space or t.is_punct:
                continue
            tt = t.text.lower().strip()
            if not tt:
                continue
            tokens.append(tt)
        return tokens

    def build(
        self,
        *,
        chunks: list[ChunkModel],
        embeddings: np.ndarray,
        doc_language: Language | None = None,
    ) -> None:
        """
        Build FAISS + BM25 indexes in memory for the provided chunks.

        embeddings: shape (len(chunks), embedding_dim)
        """

        if faiss is None:
            raise RuntimeError(
                f"faiss-cpu is required for vector search. Import error: {_FAISS_IMPORT_ERROR}"
            )
        if len(chunks) == 0:
            raise ValueError("chunks must be non-empty")

        embeddings = np.asarray(embeddings, dtype=np.float32)
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2D array")
        if embeddings.shape[0] != len(chunks):
            raise ValueError("embeddings row count must match number of chunks")
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"embeddings dim mismatch: expected {self.embedding_dim}, got {embeddings.shape[1]}"
            )

        self._chunks = chunks
        self._doc_language = doc_language or detect_dominant_language(
            " ".join(c.content for c in chunks[: min(8, len(chunks))])
        )

        # Vector index (cosine via normalized inner product).
        doc_embeddings = _l2_normalize(embeddings)
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(doc_embeddings)  # type: ignore

        # BM25 index.
        tokenized_corpus = [
            self._tokenize(c.content, language=self._doc_language) for c in chunks
        ]
        bm25 = BM25Okapi(tokenized_corpus)

        self._doc_embeddings = doc_embeddings
        self._faiss_index = index
        self._bm25 = bm25

    def search(
        self,
        *,
        query: str,
        query_embedding: np.ndarray,
        expanded_query: str | None = None,
        top_k: int = 5,
        search_dim: int | None = None,
        metrics: Optional["RetrievalMetrics"] = None,
    ) -> list[ScoredChunk]:
        """
        Search for relevant chunks.
        
        Args:
            search_dim: If specified, use MRL (Matryoshka) truncation - only use first N dimensions
                       for vector search. This speeds up search with minimal accuracy loss.
        """
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        if self._faiss_index is None or self._bm25 is None or self._doc_embeddings is None:
            raise RuntimeError("HybridRetriever is not built. Call build() first.")
        if self._doc_language is None:
            raise RuntimeError("doc_language is not set (unexpected).")

        query_embedding = np.asarray(query_embedding, dtype=np.float32).reshape(1, -1)
        if query_embedding.shape[1] != self.embedding_dim:
            raise ValueError(
                f"query_embedding dim mismatch: expected {self.embedding_dim}, got {query_embedding.shape[1]}"
            )
        
        # MRL: truncate to search_dim if specified
        use_mrl = search_dim is not None and 0 < search_dim < self.embedding_dim
        if use_mrl:
            query_emb_search = _l2_normalize(query_embedding[:, :search_dim])
            doc_emb_search = _l2_normalize(self._doc_embeddings[:, :search_dim])
        else:
            query_emb_search = _l2_normalize(query_embedding)
            doc_emb_search = self._doc_embeddings  # already normalized

        # Phase A: Vector candidates (direct cosine computation for MRL, or FAISS for full dim)
        n_docs = len(self._chunks)
        vec_fetch_k = min(max(top_k, self.candidate_k), n_docs)
        
        # Pre-compute variable to hold all MRL scores if available
        all_scores_mrl = None

        if use_mrl:
            # Direct computation for MRL (no pre-built index for truncated dims)
            scores = (query_emb_search @ doc_emb_search.T).flatten()
            all_scores_mrl = scores
            vec_ids_list = np.argsort(-scores)[:vec_fetch_k].tolist()
            vec_scores_flat = scores[vec_ids_list]
        else:
            vec_scores_raw, vec_ids = self._faiss_index.search(query_emb_search, vec_fetch_k)
            vec_ids_list = [int(i) for i in vec_ids[0] if int(i) >= 0]
            vec_scores_flat = vec_scores_raw[0][: len(vec_ids_list)]

        # Convert cosine [-1, 1] -> [0, 1] (spec expects 0..1).
        vec_scores_map: dict[int, float] = {}
        for idx, score in zip(vec_ids_list, vec_scores_flat):
            cos = float(score)
            vec_scores_map[idx] = float(np.clip((cos + 1.0) * 0.5, 0.0, 1.0))

        # Phase B: BM25 candidates.
        bm25_query = (expanded_query or query).strip()
        query_tokens = self._tokenize(bm25_query, language=self._doc_language)
        bm25_scores = np.asarray(self._bm25.get_scores(query_tokens), dtype=np.float32)

        bm25_fetch_k = min(max(top_k, self.candidate_k), n_docs)
        if bm25_fetch_k == n_docs:
            bm25_top_idx = np.argsort(-bm25_scores)
        else:
            bm25_top_idx = np.argpartition(-bm25_scores, bm25_fetch_k - 1)[:bm25_fetch_k]
            bm25_top_idx = bm25_top_idx[np.argsort(-bm25_scores[bm25_top_idx])]

        bm25_top_scores = bm25_scores[bm25_top_idx]
        bm25_min = float(np.min(bm25_top_scores)) if bm25_top_scores.size else 0.0
        bm25_max = float(np.max(bm25_top_scores)) if bm25_top_scores.size else 0.0

        def norm_bm25(raw: float) -> float:
            if bm25_max <= 0.0:
                return 0.0
            if abs(bm25_max - bm25_min) < 1e-12:
                return 1.0
            return float((raw - bm25_min) / (bm25_max - bm25_min))

        bm25_norm_map: dict[int, float] = {
            int(i): norm_bm25(float(s))
            for i, s in zip(bm25_top_idx, bm25_top_scores)
        }

        if metrics:
            metrics.add_step("bm25_search", data={
                "topk_indices": bm25_top_idx.tolist()[:10],
                "raw_scores": bm25_top_scores.tolist()[:10],
                "norm_range": (bm25_min, bm25_max)
            })

        # Phase C: Candidate union and fusion.
        candidate_ids = set(vec_ids_list) | set(int(i) for i in bm25_top_idx.tolist())

        # Compute vector scores for candidates missing from the vector search top-k
        missing_indices = [idx for idx in candidate_ids if idx not in vec_scores_map]
        if missing_indices:
            if all_scores_mrl is not None:
                # Optimized MRL: O(1) lookup since we computed all scores
                for idx in missing_indices:
                    cos = float(all_scores_mrl[idx])
                    vec_scores_map[idx] = float(np.clip((cos + 1.0) * 0.5, 0.0, 1.0))
            else:
                # Optimized Vectorization: Compute all missing scores in one batch (M, D) @ (1, D).T
                # instead of iterating with np.dot one by one.
                missing_vecs = self._doc_embeddings[missing_indices]
                # (M, Dim) @ (1, Dim).T -> (M, 1)
                missing_scores = missing_vecs @ query_emb_search.T
                missing_scores_flat = missing_scores.reshape(-1)

                for idx, raw_score in zip(missing_indices, missing_scores_flat):
                    cos = float(raw_score)
                    vec_scores_map[idx] = float(np.clip((cos + 1.0) * 0.5, 0.0, 1.0))

        scored: list[ScoredChunk] = []
        for idx in candidate_ids:
            # All candidates should now be in vec_scores_map
            vector_score = vec_scores_map.get(idx, 0.0)  # fallback 0.0 just in case
            bm25_norm = bm25_norm_map.get(idx, 0.0)
            final = (self.vector_weight * vector_score) + (self.bm25_weight * bm25_norm)
            scored.append(
                ScoredChunk(
                    chunk=self._chunks[idx],
                    final_score=float(final),
                    vector_score=float(vector_score),
                    bm25_score_norm=float(bm25_norm),
                )
            )

        scored.sort(key=lambda x: x.final_score, reverse=True)
        if metrics:
            metrics.add_step("hybrid_fusion", data={
                "topk_chunks": [
                    {
                        "chunk_id": s.chunk.id,
                        "chunk_idx": self._chunks.index(s.chunk),
                        "final_score": s.final_score,
                        "vector_score": s.vector_score,
                        "bm25_norm": s.bm25_score_norm
                    } for s in scored[:top_k]
                ]
            })
        return scored[: min(top_k, len(scored))]
