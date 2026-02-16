## ADDED Requirements

### Requirement: Backend Orchestration Must Be Modularized by Responsibility
The backend SHALL separate HTTP routes, chat orchestration, and ingestion orchestration into dedicated modules.

#### Scenario: Reading backend entrypoint
- **WHEN** engineers inspect backend app entrypoint
- **THEN** lifecycle/bootstrap concerns are isolated from chat/ingestion business workflows

#### Scenario: Chat workflow maintenance
- **WHEN** engineers update retrieval or answer-generation logic
- **THEN** changes are localized to chat pipeline module without route-layer rewrites
