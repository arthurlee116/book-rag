## ADDED Requirements

### Requirement: Embedding Instruction Template Default Must Follow Canonical Query Label Format
The default embedding instruction template SHALL use `Query: {query}` label format with a separating space after the colon.

#### Scenario: No env override for instruction template
- **WHEN** backend loads default embedding query instruction template
- **THEN** template renders as `Instruct: {task}\nQuery: {query}`

### Requirement: JSON Fence Cleanup Must Correctly Parse Whitespace
Structured-output extraction SHALL correctly remove markdown code fences using valid whitespace regex patterns.

#### Scenario: Model output wrapped in fenced JSON block
- **WHEN** model returns output inside ```json fenced block
- **THEN** extraction logic strips fences and parses contained JSON payload
