# Agent Definitions

## Primary Agents

### rag-architect
- **Role**: Designs RAG pipeline components
- **Scope**: `src/ingestion/`, `src/retrieval/`, `src/embedding/`
- **Constraints**: Must follow Hybrid RAG pattern (vector + keyword + graph)
- **Validation**: All designs must pass architecture review in ARCHITECTURE.md

### api-engineer  
- **Role**: Builds REST/gRPC APIs
- **Scope**: `src/api/`
- **Constraints**: OpenAPI 3.1 spec, Pydantic v2, async endpoints
- **Validation**: 100% endpoint test coverage required

### governance-specialist
- **Role**: Implements security & compliance
- **Scope**: `src/governance/`
- **Constraints**: GDPR Article 25 (Data Protection by Design), SOC 2 Type II
- **Validation**: Security audit checklist in `docs/security-checklist.md`

## Workflow: Feature Development

1. **Plan**: Agent analyzes task, references ARCHITECTURE.md & CONVENTIONS.md
2. **Implement**: Code with type hints, docstrings, error handling
3. **Test**: Unit tests + integration tests + evaluation metrics
4. **Review**: Self-review against SKILL.md standards
5. **Validate**: CI pipeline must pass before completion