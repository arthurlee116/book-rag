## ADDED Requirements

### Requirement: Ingestion Chunking Must Fail Safe
The ingestion pipeline SHALL catch chunking-stage exceptions and transition the session to an explicit error state instead of leaving ingestion in processing state.

#### Scenario: Chunking raises runtime exception
- **WHEN** document parsing succeeds but chunking throws an exception
- **THEN** session ingest status becomes `error`
- **AND** session ingest error contains failure details
- **AND** logs include a chunking error entry
