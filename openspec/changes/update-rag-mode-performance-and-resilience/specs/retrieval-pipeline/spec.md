## ADDED Requirements

### Requirement: Translation Alignment Must Fail Open
The chat pipeline SHALL continue retrieval and answer generation using the original query when translation/language-alignment API calls fail.

#### Scenario: Translation API error
- **WHEN** language alignment fails with an upstream API error
- **THEN** the backend continues with the original user query
- **AND** the request does not fail solely due to translation failure

### Requirement: HyDE Toggle Independence
HyDE execution SHALL be controlled independently from query-fusion execution.

#### Scenario: HyDE on while query fusion off
- **WHEN** `ERR_HYDE_ENABLED=true` and `ERR_QUERY_FUSION_ENABLED=false`
- **THEN** the pipeline still generates and uses HyDE retrieval candidates

### Requirement: Retry Policy Must Be Transient-Only
OpenRouter requests SHALL retry only transient/network failures and SHALL NOT retry deterministic client-side failures.

#### Scenario: Deterministic 4xx error
- **WHEN** an OpenRouter request returns a deterministic 4xx error
- **THEN** the backend does not retry the request repeatedly

#### Scenario: 429 or 5xx transient error
- **WHEN** an OpenRouter request fails with 429 or 5xx
- **THEN** the backend retries up to configured attempts with backoff

### Requirement: Normal Mode Parallelism
The normal-mode retrieval pipeline SHALL execute independent preprocessing and retrieval tasks concurrently with bounded concurrency.

#### Scenario: Independent preprocessing tasks
- **WHEN** query variants and HyDE are both enabled
- **THEN** they are generated concurrently

#### Scenario: Multi-query retrieval
- **WHEN** multiple query embeddings are available
- **THEN** retrieval calls execute concurrently under a concurrency bound

### Requirement: Retriever Hot Path Efficiency
Retriever top-k operations SHALL avoid unnecessary full sorting and repeated linear scans in request hot paths.

#### Scenario: MRL search top-k
- **WHEN** MRL search is used
- **THEN** top-k selection uses partial selection instead of full sort

#### Scenario: Metrics with chunk indices
- **WHEN** retrieval metrics include chunk indices
- **THEN** chunk index lookup is O(1) per chunk

### Requirement: Configuration Default Consistency
Configuration defaults SHALL be consistent between static model defaults and environment-loader defaults for the same setting.

#### Scenario: No env overrides
- **WHEN** no relevant env variables are set
- **THEN** `Settings()` defaults and `load_settings()` defaults produce consistent values for shared fields
