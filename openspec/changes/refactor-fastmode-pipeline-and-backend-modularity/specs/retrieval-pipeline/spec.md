## ADDED Requirements

### Requirement: Language Alignment Must Be Conditional Instead of Always-On
The retrieval pipeline SHALL skip language-alignment translation calls when the query language is already aligned with the document language, unless explicitly forced by configuration.

#### Scenario: Query and document language already aligned
- **WHEN** the query language equals the document language
- **THEN** the pipeline skips translation/alignment API call
- **AND** retrieval continues using the original query text

#### Scenario: Cross-language query
- **WHEN** the query language differs from the document language
- **THEN** the pipeline performs language alignment before lexical retrieval

### Requirement: HyDE Retrieval Must Avoid Redundant BM25 Work
HyDE retrieval candidates SHALL support vector-only retrieval so that HyDE does not trigger duplicate BM25 computation for the same lexical query.

#### Scenario: HyDE branch executes
- **WHEN** HyDE is enabled and selected for retrieval
- **THEN** HyDE retrieval uses vector scoring without BM25 scoring
- **AND** fused ranking still includes HyDE-derived candidates

### Requirement: Fast Mode Candidate Pool Must Be Tunable
Fast mode SHALL use a dedicated candidate-k override instead of inheriting a fixed large candidate_k tuned for normal mode.

#### Scenario: Fast mode retrieval search
- **WHEN** fast mode is enabled
- **THEN** retriever search uses fast-mode candidate-k override
- **AND** the value is configurable via environment setting

### Requirement: Fast Mode Query Embedding Must Use Weighted Aggregation
Fast mode query embedding aggregation SHALL use weighted averaging (not plain mean), prioritizing original user-query representations.

#### Scenario: Fast mode with original and aligned query variants
- **WHEN** fast mode embeds multiple query forms
- **THEN** aggregation assigns higher influence to earlier/original query embeddings

### Requirement: Fast Mode Must Apply Re-Packing Strategy
Fast mode SHALL apply configured context re-packing strategy instead of unconditionally skipping re-packing.

#### Scenario: Fast mode answer context assembly
- **WHEN** fast mode final context is prepared
- **THEN** context chunks are ordered according to configured repack strategy

### Requirement: MRL Retrieval Must Use FAISS Index Path
When MRL dimension truncation is requested, retriever SHALL use cached FAISS inner-product indexes at the requested truncated dimension.

#### Scenario: Repeated fast-mode searches with same MRL dimension
- **WHEN** multiple searches use the same truncated dimension
- **THEN** retriever reuses cached MRL FAISS index
- **AND** avoids per-request full-matrix top-k search
