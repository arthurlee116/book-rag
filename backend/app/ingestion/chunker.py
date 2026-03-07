from __future__ import annotations

import os
import re
from typing import Any
from uuid import uuid4

import numpy as np

from ..models.chunk import ChunkModel
from .file_parser import ParsedBlock

try:
    import spacy
except ImportError:
    spacy = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # type: ignore


_SHARED_EMBED_MODEL: Any | None = None
_SHARED_EMBED_MODEL_NAME: str | None = None


def estimate_tokens(text: str) -> int:
    """
    Lightweight token estimate (no tokenizer dependency).
    - CJK chars count as ~1 token each
    - Latin words (whitespace-separated runs of non-CJK) count as ~1 token each
    Uses character iteration instead of re.findall to avoid allocating
    temporary string lists on every call.
    """
    if not text:
        return 0
    cjk = 0
    latin_words = 0
    in_word = False
    for c in text:
        if "\u4e00" <= c <= "\u9fff":
            cjk += 1
            if in_word:
                latin_words += 1
                in_word = False
        elif c.isalnum():
            if not in_word:
                in_word = True
        else:
            if in_word:
                latin_words += 1
                in_word = False
    if in_word:
        latin_words += 1
    return cjk + latin_words


class Chunker:
    def __init__(
        self,
        *,
        target_tokens: int = 512,
        overlap_tokens: int = 50,
        semantic_enabled: bool = False,
        semantic_threshold: float = 0.5,
        semantic_max_sentences: int = 2000,
        semantic_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.target_tokens = max(1, int(target_tokens))
        self.overlap_tokens = max(0, int(overlap_tokens))
        self.semantic_enabled = semantic_enabled
        self.semantic_threshold = float(semantic_threshold)
        self.semantic_max_sentences = max(1, int(semantic_max_sentences))
        self.semantic_model_name = (semantic_model_name or "all-MiniLM-L6-v2").strip()

        self._spacy_nlp: Any | None = None
        self._embed_model: Any | None = None
        self._embed_model_failed = False

    def _apply_hf_env(self) -> None:
        proxy = (
            os.getenv("ERR_HF_PROXY") or os.getenv("ERR_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
        )
        if proxy:
            os.environ.setdefault("HTTPS_PROXY", proxy)
            os.environ.setdefault("HTTP_PROXY", proxy)

        hf_home = os.getenv("ERR_HF_HOME")
        if hf_home:
            os.environ.setdefault("HF_HOME", hf_home)

        ca_bundle = os.getenv("ERR_HF_CA_BUNDLE")
        if ca_bundle:
            os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)
            os.environ.setdefault("SSL_CERT_FILE", ca_bundle)

        raw_disable_ssl = os.getenv("ERR_HF_DISABLE_SSL_VERIFY")
        if raw_disable_ssl and raw_disable_ssl.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }:
            os.environ.setdefault("HF_HUB_DISABLE_SSL_VERIFY", "1")

    def _ensure_spacy(self) -> None:
        if self._spacy_nlp is not None:
            return
        if spacy is None:
            return
        try:
            self._spacy_nlp = spacy.blank("en")
            self._spacy_nlp.add_pipe("sentencizer")
        except Exception:
            self._spacy_nlp = None

    def _ensure_embed_model(self) -> None:
        if self._embed_model is not None or self._embed_model_failed:
            return
        if not self.semantic_enabled:
            return
        if SentenceTransformer is None:
            self._embed_model_failed = True
            return

        global _SHARED_EMBED_MODEL, _SHARED_EMBED_MODEL_NAME

        if _SHARED_EMBED_MODEL is not None and _SHARED_EMBED_MODEL_NAME == self.semantic_model_name:
            self._embed_model = _SHARED_EMBED_MODEL
            return

        try:
            self._apply_hf_env()
            model = SentenceTransformer(self.semantic_model_name, device="cpu")
        except Exception:
            self._embed_model_failed = True
            return

        _SHARED_EMBED_MODEL = model
        _SHARED_EMBED_MODEL_NAME = self.semantic_model_name
        self._embed_model = model

    def _split_sentences(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []

        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        if cjk_count > len(text) * 0.3:
            parts = re.split(r"([。？！\n])", text)
            sentences: list[str] = []
            current = ""
            for p in parts:
                current += p
                if p in "。？！\n":
                    if current.strip():
                        sentences.append(current.strip())
                    current = ""
            if current.strip():
                sentences.append(current.strip())
            return sentences

        self._ensure_spacy()
        if self._spacy_nlp is not None:
            doc = self._spacy_nlp(text)
            return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

        # Fallback sentence splitter.
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    def _calculate_cosine_distances(self, sentences: list[str]) -> list[float]:
        if len(sentences) < 2:
            return []

        self._ensure_embed_model()
        if not self._embed_model:
            return [0.0] * (len(sentences) - 1)

        embeddings = self._embed_model.encode(sentences)
        embeddings = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-12)

        sims = np.sum(embeddings[:-1] * embeddings[1:], axis=1)
        dists = 1.0 - sims
        return dists.tolist()

    def chunk(self, *, blocks: list[ParsedBlock]) -> list[ChunkModel]:
        all_sentences: list[dict[str, Any]] = []

        for block in blocks:
            txt = block.text.strip()
            if not txt:
                continue

            for sent in self._split_sentences(txt):
                all_sentences.append(
                    {
                        "text": sent,
                        "rich": sent,
                        "metadata": dict(block.metadata),
                        "tokens": estimate_tokens(sent),
                    }
                )

        if not all_sentences:
            return []

        raw_texts = [item["text"] for item in all_sentences]
        use_semantic = self.semantic_enabled and len(raw_texts) > 1
        if use_semantic and len(raw_texts) > self.semantic_max_sentences:
            use_semantic = False

        if use_semantic:
            try:
                distances = self._calculate_cosine_distances(raw_texts)
            except Exception:
                distances = [0.0] * (len(raw_texts) - 1)
        else:
            distances = [0.0] * (len(raw_texts) - 1)

        chunks: list[ChunkModel] = []
        current_chunk_sents: list[dict[str, Any]] = []
        current_tokens = 0
        min_semantic_split_tokens = max(20, min(50, self.target_tokens // 2))

        for i, sent_dict in enumerate(all_sentences):
            sent_tokens_val = int(sent_dict["tokens"])

            if current_chunk_sents and (current_tokens + sent_tokens_val > self.target_tokens):
                overlap_sents, overlap_tokens = self._get_overlap_sents(current_chunk_sents)
                self._flush_chunk(chunks, current_chunk_sents)
                current_chunk_sents = overlap_sents
                current_tokens = overlap_tokens

            current_chunk_sents.append(sent_dict)
            current_tokens += sent_tokens_val

            should_split = False
            if use_semantic and i < len(distances):
                if distances[i] > self.semantic_threshold and current_tokens >= min_semantic_split_tokens:
                    should_split = True

            if should_split:
                overlap_sents, overlap_tokens = self._get_overlap_sents(current_chunk_sents)
                self._flush_chunk(chunks, current_chunk_sents)
                current_chunk_sents = overlap_sents
                current_tokens = overlap_tokens

        if current_chunk_sents:
            self._flush_chunk(chunks, current_chunk_sents)

        for i in range(len(chunks)):
            chunks[i].prev_content = chunks[i - 1].content if i > 0 else None
            chunks[i].next_content = chunks[i + 1].content if i < (len(chunks) - 1) else None

        return chunks

    def _get_overlap_sents(self, sents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        if self.overlap_tokens <= 0 or not sents:
            return [], 0

        overlap: list[dict[str, Any]] = []
        tokens = 0
        for sent in reversed(sents):
            sent_tokens = int(sent["tokens"])
            if tokens + sent_tokens > self.overlap_tokens and overlap:
                break
            overlap.append(sent)
            tokens += sent_tokens
            if tokens >= self.overlap_tokens:
                break

        overlap.reverse()
        return overlap, tokens

    def _flush_chunk(self, chunks_list: list[ChunkModel], sents: list[dict[str, Any]]) -> None:
        if not sents:
            return

        content = " ".join(s["text"] for s in sents)
        rich_content = " ".join(s["rich"] for s in sents)

        combined_meta: dict[str, Any] = {}
        for s in sents:
            combined_meta.update(s["metadata"])

        chunks_list.append(
            ChunkModel(
                id=uuid4().hex,
                content=content,
                rich_content=rich_content,
                metadata={**combined_meta, "chunk_index": len(chunks_list)},
            )
        )
