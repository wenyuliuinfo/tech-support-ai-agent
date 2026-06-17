# Coding Conventions

## Python Standards
- **Framework**: FastAPI for APIs, Pydantic v2 for validation, PostgreSQL for DB
- **Async**: All I/O operations must be async (database, HTTP, file)
- **Types**: 100% type hints, strict mypy (`--strict` mode)
- **Error Handling**: Custom exception hierarchy, structured logging with trace IDs

## RAG-Specific Patterns
- **Pipeline Pattern**: All data flows use async generators with back-pressure
- **Circuit Breakers**: External service calls (LLM, vector DB) must have circuit breakers
- **Observability**: OpenTelemetry spans for every retrieval step, Prometheus metrics

## Security
- No secrets in code (use AWS Secrets Manager / HashiCorp Vault)
- PII detection before embedding (presidio-anonymizer)
- Input sanitization on all user queries (SQL injection, prompt injection)
- Rate limiting: 100 req/min per user, 1000 req/min per tenant