## ADDED Requirements

### Requirement: BM25 Backend Must Use Scalable Sparse Implementation
The backend SHALL use a BM25 implementation optimized for sparse-matrix retrieval workloads to improve performance at larger chunk counts.

#### Scenario: Building lexical index for document chunks
- **WHEN** ingestion builds lexical retrieval structures
- **THEN** it uses the configured scalable BM25 backend
- **AND** lexical top-k retrieval remains available for hybrid fusion

### Requirement: English BM25 Tokenization Must Be Lightweight
English lexical tokenization in BM25 hot path SHALL use lightweight tokenization instead of full NLP pipeline tokenization.

#### Scenario: English lexical query tokenization
- **WHEN** document language is English
- **THEN** tokenizer performs lightweight normalization/token splitting
- **AND** avoids heavy pipeline initialization in retrieval hot path
