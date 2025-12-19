from __future__ import annotations

import re
from typing import Any
from uuid import uuid4
import numpy as np

from ..models.chunk import ChunkModel
from .file_parser import ParsedBlock

try:
    import spacy
except ImportError:
    spacy = None

try:
    import jieba
except ImportError:
    jieba = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None


def estimate_tokens(text: str) -> int:
    """
    Lightweight token estimate (no tokenizer dependency).
    - CJK chars count as ~1 token each
    - Latin words/numbers count as ~1 token each
    """

    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z0-9]+", text))
    return cjk + latin


class Chunker:
    def __init__(
        self,
        *,
        target_tokens: int = 512,
        overlap_tokens: int = 50,
        semantic_enabled: bool = False,
        semantic_threshold: float = 0.5,
    ) -> None:
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.semantic_enabled = semantic_enabled
        self.semantic_threshold = semantic_threshold
        
        self._spacy_nlp = None
        self._embed_model = None

    def _ensure_spacy(self) -> None:
        if self._spacy_nlp is not None:
            return
        if spacy is None:
            # Fallback if spacy not installed, though it should be
             print("Warning: spacy not installed, falling back to simple split")
             return
        try:
             self._spacy_nlp = spacy.blank("en")
             self._spacy_nlp.add_pipe("sentencizer")
        except Exception as e:
            print(f"Error loading spacy: {e}")

    def _ensure_embed_model(self) -> None:
        if self._embed_model is not None:
            return
        if SentenceTransformer is None:
             print("Warning: sentence-transformers not installed")
             return
        # lightweight model
        try:
            self._embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        except Exception as e:
             print(f"Error loading embedding model: {e}")

    def _split_sentences(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
            
        # Hard check for CJK dominance -> use regex/jieba-like splitting
        cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        if cjk_count > len(text) * 0.3:
             # Simple CJK splitter on punctuation
             # Split by 。 ？ ！ \n
             parts = re.split(r"([。？！\n])", text)
             sentences = []
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
        if self._spacy_nlp:
             doc = self._spacy_nlp(text)
             return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Fallback
        return [s.strip() for s in text.split(". ") if s.strip()]

    def _calculate_cosine_distances(self, sentences: list[str]) -> list[float]:
        if len(sentences) < 2:
            return []
        
        self._ensure_embed_model()
        if not self._embed_model:
            return [0.0] * (len(sentences) - 1)
            
        embeddings = self._embed_model.encode(sentences)
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / (norms + 1e-12)
        
        # Calculate cosine similarity between adjacent (i, i+1)
        sims = np.sum(embeddings[:-1] * embeddings[1:], axis=1)
        # Distance = 1 - similarity
        dists = 1 - sims
        return dists.tolist()

    def chunk(self, *, blocks: list[ParsedBlock]) -> list[ChunkModel]:
        # Flatten blocks into a single stream of sentences, preserving block metadata per sentence if needed?
        # Actually, simpler to just treat blocks as source of text.
        # But we want to preserve rich text if possible. 
        # For semantic chunking, we'll simplify: reconstruct full text, split to sentences, then grouping.
        # This loses per-block rich text alignment, but that's a trade-off. 
        # Alternatively, split each block into sentences and keeping track of parent block.

        if not self.semantic_enabled:
             # Use legacy logic or reimplement valid fixed-size logic here?
             # For now, let's just use the semantic logic but with threshold=0 which equates to filling buffer?
             # No, better to stick to pure semantic path if enabled.
             pass

        # 1. Flatten all text
        all_sentences: list[dict[str, Any]] = [] # {text, rich, metadata}
        
        for block in blocks:
             txt = block.text.strip()
             if not txt: continue
             
             sents = self._split_sentences(txt)
             for s in sents:
                 # heuristic to try and find rich text equiv? Too hard.
                 # We will just map rich text = text for now inside chunks, 
                 # or if the block was small enough, use block's rich text. 
                 # Let's assume plain text for semantic chunks for simplicity for now.
                 all_sentences.append({
                     "text": s,
                     "rich": s, # simplified
                     "metadata": block.metadata
                 })
        
        if not all_sentences:
            return []
            
        # 2. Assign token counts
        for item in all_sentences:
            item["tokens"] = estimate_tokens(item["text"])

        # 3. If semantic, calc distances
        # We can calculate distances for the whole batch or sliding window. 
        # For valid large docs, batching all might be heavy. But typically docs are < 100k tokens.
        # 300 pages book ~100-150k words. 
        # Let's process in groups if needed, but for "Research Files" usually short.
        
        raw_texts = [x["text"] for x in all_sentences]
        distances = []
        if self.semantic_enabled and len(raw_texts) > 1:
            try:
                distances = self._calculate_cosine_distances(raw_texts)
            except Exception as e:
                print(f"Semantic calc failed: {e}, falling back to fixed")
                distances = [0.0] * (len(raw_texts) - 1)
        else:
             distances = [0.0] * (len(raw_texts) - 1)

        # 4. Group into chunks
        chunks: list[ChunkModel] = []
        
        current_chunk_sents: list[dict] = []
        current_tokens = 0
        
        # dist[i] is between sent[i] and sent[i+1]
        
        for i, sent in enumerate(all_sentences):
            # Special case: if single sentence is > target_tokens, we must split it forcefully
            # For simplicity in this implementation, we will just allow it to overflow if it's one sentence, 
            # UNLESS it is excessively large (e.g. > 2x target). 
            # Better approach: if sent["tokens"] > target_tokens, split sent["text"] into smaller pieces first.
            # But `_split_sentences` is responsible for splitting.
            # Let's add a check here to force flush previous if adding this one exceeds limit significantly,
            # and if this one alone is huge, we might just have to accept it or implement sub-sentence splitting.
            # For now: strict flush BEFORE adding if adding would exceed limit, unless buffer is empty.
            
            if current_chunk_sents and (current_tokens + sent["tokens"] > self.target_tokens):
                 # Flush current buffer first
                 overlap_sents, overlap_tokens = self._get_overlap_sents(current_chunk_sents)
                 self._flush_chunk(chunks, current_chunk_sents)
                 current_chunk_sents = overlap_sents
                 current_tokens = overlap_tokens
            
            current_chunk_sents.append(sent)
            current_tokens += sent["tokens"]
            
            # Check for semantic split trigger
            should_split = False
            
            # Semantic split
            # Check distance to NEXT sentence if exists
            if self.semantic_enabled and i < len(distances):
                 dist = distances[i]
                 if dist > self.semantic_threshold and current_tokens > 50: # min chunk size
                      should_split = True
            
            if should_split:
                 overlap_sents, overlap_tokens = self._get_overlap_sents(current_chunk_sents)
                 self._flush_chunk(chunks, current_chunk_sents)
                 current_chunk_sents = overlap_sents
                 current_tokens = overlap_tokens
        
        # Flush remainder
        if current_chunk_sents:
             self._flush_chunk(chunks, current_chunk_sents)

        # add prev/next
        for i in range(len(chunks)):
            chunks[i].prev_content = chunks[i - 1].content if i > 0 else None
            chunks[i].next_content = chunks[i + 1].content if i < (len(chunks) - 1) else None

        return chunks

    def _get_overlap_sents(self, sents: list[dict]) -> tuple[list[dict], int]:
        if self.overlap_tokens <= 0 or not sents:
            return [], 0

        overlap: list[dict] = []
        tokens = 0
        for sent in reversed(sents):
            sent_tokens = sent["tokens"]
            if tokens + sent_tokens > self.overlap_tokens and overlap:
                break
            overlap.append(sent)
            tokens += sent_tokens
            if tokens >= self.overlap_tokens:
                break

        overlap.reverse()
        return overlap, tokens

    def _flush_chunk(self, chunks_list: list[ChunkModel], sents: list[dict]) -> None:
        if not sents: return
        
        content = " ".join(s["text"] for s in sents)
        # Merge metadata priority? Last one? First one?
        # Usually first one has chapter title.
        combined_meta = {}
        for s in sents:
            combined_meta.update(s["metadata"])
            
        chunks_list.append(ChunkModel(
            id=uuid4().hex,
            content=content,
            rich_content=content, # simplified
            metadata={**combined_meta, "chunk_index": len(chunks_list)}
        ))
