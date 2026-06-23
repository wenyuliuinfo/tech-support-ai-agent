# Coding Conventions

## Python Standards
- **Framework**: FastAPI for APIs, Pydantic v2 for validation, PostgreSQL for DB
- **Async**: All I/O operations must be async (database, HTTP, file)
- **Types**: 100% type hints, strict mypy (`--strict` mode)
- **Error Handling**: Custom exception hierarchy, structured logging with trace IDs
- **Runner**: pnpm is used as the unified task runner for both frontend and backend


## Backend Layering
`src/app/` is organized into three layers. Each layer has a single responsibility, and imports flow in one direction only: **routers → services → repositories**. A layer may never import from a layer above it.
    ```
    src/app/
    ├── routers/            # HTTP/SSE boundary
    ├── services/           # business logic / orchestration
    ├── repositories/       # external system access
    └── tests/
    ```

### `routers/`
- Defines FastAPI route handlers (`GET /tickets`, `POST /chat`, `GET /health`).
- Owns request/response Pydantic models and input validation.
- Extracts `account_id` from the validated auth token — never from a request body or query param (see ARCHITECTURE.md §3.1.1 / §10.1).
- Contains no business logic and no direct calls to Pinecone, OpenAI, or PostgreSQL. Delegates to `services/`.
- May import from: `services/`.
- May not import from: `repositories/`.

### `services/`
- Contains business logic: retrieval orchestration, prompt construction, conflict handling (ARCHITECTURE.md §6–§7), chunking policy, ingestion pipeline logic.
- Coordinates one or more repositories to fulfill a request. Does not know about HTTP, SSE framing, or FastAPI request/response objects.
- May import from: `repositories/`.
- May not import from: `routers/`.

### `repositories/`
- The only layer permitted to import SDKs for external systems: the `pinecone-client` SDK, the `openai` SDK, and SQLAlchemy/`asyncpg`.
- Each repository wraps exactly one external system (e.g.`PineconeRepository`, `TicketRepository`, `OpenAIRepository`) and exposes plain async methods with typed inputs/outputs — no SDK-specific types leak past this layer.
- Contains no business logic — a repository method does one thing (e.g. `query_chunks(embedding, k) -> list[ChunkResult]`), it does not decide retrieval priority or apply the conflict-handling rules in §7.4.
- May not import from `routers/` or `services/`.

### Why this boundary matters for this project specifically
- Keeps the citation-format contract (ARCHITECTURE.md §2) and the conflict-handling logic (§7.4) testable in isolation from FastAPI and from real network calls to Pinecone/OpenAI — `services/` can be unit tested with fake repositories.
- Makes account-scoping enforceable mechanically: any database query touching `tickets` lives in exactly one place (`repositories/ticket.py`), so the structural test that checks "every ticket query filters by
  `account_id`" only has one file to scan, not the whole codebase.
- New external dependencies (a different vector DB, a different LLM provider) only ever touch `repositories/` — `services/` and `routers/` stay unchanged, which is what makes a future provider swap a contained, reviewable change rather than a rewrite.

## RAG-Specific Patterns
- **Pipeline Pattern**: All data flows use async generators with back-pressure
- **Circuit Breakers**: External service calls (LLM, vector DB) must have circuit breakers
- **Observability**: OpenTelemetry spans for every retrieval step, Prometheus metrics

## Security
- No secrets in code (use AWS Secrets Manager / HashiCorp Vault)
- PII detection before embedding (presidio-anonymizer)
- Input sanitization on all user queries (SQL injection, prompt injection)
- Rate limiting: 1000 req/min per account

