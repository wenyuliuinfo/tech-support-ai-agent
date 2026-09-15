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
- Contains no business logic and no direct calls to Pinecone, OpenAI, PostgreSQL, or MinIO. Delegates to `services/`.
- May import from: `services/`.
- May not import from: `repositories/`.

### `services/`
- Contains business logic: retrieval orchestration, prompt construction, conflict handling (ARCHITECTURE.md §6–§7), chunking policy, ingestion pipeline logic, document parsing dispatch (`services/ingestion/parsers/`).
- Coordinates one or more repositories to fulfill a request. Does not know about HTTP, SSE framing, or FastAPI request/response objects.
- Format-specific parsers (`markdown.py`, `pdf.py`, `docx.py`) are pure functions — they take raw `bytes` in and return `list[ParsedSection]` out, with no repository calls of their own, so they're unit-testable without a running MinIO or Postgres instance.
- May import from: `repositories/`.
- May not import from: `routers/`.

### `repositories/`
- The only layer permitted to import SDKs for external systems: the `pinecone-client` SDK, the `openai` SDK, SQLAlchemy/`asyncpg`, and the MinIO/`boto3` client.
- Each repository wraps exactly one external system (e.g. `PineconeRepository`, `TicketRepository`, `OpenAIRepository`, `StorageRepository`) and exposes plain async methods with typed inputs/outputs — no SDK-specific types leak past this layer.
- `StorageRepository` (MinIO) exposes `upload(key, content, content_type) -> StorageObject`, `get(key) -> bytes`, `list(prefix) -> list[StorageObject]`, and `archive(key)`. No other layer imports the MinIO SDK or `boto3` directly.
- Contains no business logic — a repository method does one thing (e.g. `query_chunks(embedding, k) -> list[ChunkResult]`), it does not decide retrieval priority or apply the conflict-handling rules in §7.4.
- May not import from `routers/` or `services/`.

### Why this boundary matters for this project specifically
- Keeps the citation-format contract (ARCHITECTURE.md §2) and the conflict-handling logic (§7.4) testable in isolation from FastAPI and from real network calls to Pinecone/OpenAI/MinIO — `services/` can be unit tested with fake repositories.
- Makes account-scoping enforceable mechanically: any database query touching `tickets` lives in exactly one place (`repositories/ticket.py`), so the structural test that checks "every ticket query filters by `account_id`" only has one file to scan, not the whole codebase.
- New external dependencies (a different vector DB, a different LLM provider, a different object store) only ever touch `repositories/` — `services/` and `routers/` stay unchanged, which is what makes a future provider swap a contained, reviewable change rather than a rewrite.

## RAG-Specific Patterns
- **Pipeline Pattern**: All data flows use async generators with back-pressure
- **Circuit Breakers**: External service calls (LLM, vector DB, object storage) must have circuit breakers
- **Observability**: OpenTelemetry spans for every retrieval step, Prometheus metrics
- **Format-agnostic chunking**: The chunker operates on the parser-normalized `ParsedSection` stream regardless of source format (`.md`, `.pdf`, `.docx`) — no format-specific logic belongs in `services/ingestion/pipeline.py` or below

## Security
- No secrets in code (use AWS Secrets Manager / HashiCorp Vault) — this includes MinIO access/secret keys
- PII detection before embedding (presidio-anonymizer)
- Input sanitization on all user queries (SQL injection, prompt injection)
- Rate limiting: 1000 req/min per account
- Reject documents that yield empty/near-empty extracted text (e.g. scanned/image-only PDFs) at ingestion time rather than silently upserting empty chunks
