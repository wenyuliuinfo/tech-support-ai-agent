# Agent Definitions
This is the authoritative control surface for all coding agents. Read this first.

## 0. Doc Read Order
Before making changes, read documents in this order:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `ARCHITECTURE.md`
4. relevant ADRs in `docs/adr/`
5. `CONVENTIONS.md`
6. `REVIEW-STANDARDS.md`

## 1. Repository Map
Target repository layout:
```
src/web/                Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
src/app/                FastAPI backend: routers/, services/, repositories/
infra/                  Deployment config
docs/knowledge_base     Documentation for building agent knowledge base
docs/adr/               ADRs definition for agent reference
```

## 2. Primary Agents

### rag-architect
- **Role**: Designs RAG pipeline components
- **Constraints**: Must follow RAG pattern
- **Validation**: All designs must pass architecture review in ARCHITECTURE.md

### api-engineer  
- **Role**: Builds REST/SSE APIs
- **Scope**: `src/app/routers/`
- **Constraints**: OpenAPI 3.1 spec, Pydantic v2, async endpoints
- **Validation**: Above 80% endpoint test coverage required

### frontend-engineer
- **Role**: Builds Next.js frontend UI and client-side streaming logic
- **Scope**: `src/web/`
- **Constraints**: Next.js 16 App Router, Tailwind v4, shadcn/ui, React Server Components by default, client components only for interactivity
- **Validation**: 
  - All chat UI must handle SSE `text/event-stream` parsing correctly
  - Must display citations inline with answer text per ARCHITECTURE.md §2 citation format
  - Must scope ticket display to authenticated account only
  - Above 80% component test coverage (Vitest + React Testing Library)

### ingestion-engineer
- **Role**: Builds offline ingestion pipeline for Knowledge Base Documents
- **Scope**: `src/app/services/`
- **Constraints**: 
  - Must produce deterministic chunk IDs per ARCHITECTURE.md §8.6
  - Must preserve metadata fields in §8.4 exactly
  - Must handle tombstoning for deleted documents
  - Must be idempotent: repeated runs on unchanged files produce no vector store mutations
- **Validation**:
  - Ingestion tests must verify chunk boundary stability
  - Must pass structural test: `chunk_id == f"{document_id}_{chunk_index}_{content_hash}"`
  - Must log ingestion_version and updated_at for every upsert

### 2.1 Agent Collaboration Rules

| When this changes... | These agents must re-run validation |
|----------------------|-------------------------------------|
| `ARCHITECTURE.md` §3–§8 | `rag-architect` → `api-engineer` → `frontend-engineer` |
| `docs/knowledge_base/*` | `ingestion-engineer` (triggers re-ingestion) |
| `src/app/routers/*` | `api-engineer` (self), `frontend-engineer` (contract check) |
| `src/web/components/chat/*` | `frontend-engineer` (self), `api-engineer` (SSE contract check) |
| `src/app/repositories/*` | `api-engineer` (self), `rag-architect` (retrieval quality) |

**Handoff artifacts:**
- `rag-architect` produces `docs/adr/<feature>-design.md` before `api-engineer` implements
- `api-engineer` produces OpenAPI spec fragment before `frontend-engineer` builds against it
- `ingestion-engineer` produces `docs/ingestion/INDEX.md` manifest after each run


## 3. Quality Expectations
### Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### Simplicity First
Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

### Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.


## 4. Command
```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm ingest            # run full ingestion pipeline on docs/knowledge_base/
pnpm ingest:dry        # dry-run: compute chunks and metadata without upserting
pnpm ingest:verify     # verify vector store matches local KB manifest
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```


## 5. Workflow: Feature Development
### 5.1 Plan
Agent analyzes task, references ARCHITECTURE.md & CONVENTIONS.md.
- If task touches retrieval or chunking: `rag-architect` leads
- If task touches API contracts or SSE streaming: `api-engineer` leads
- If task touches chat UI or ticket display: `frontend-engineer` leads
- If task touches document processing or re-indexing: `ingestion-engineer` leads

### 5.2 Implement
Code with type hints, docstrings, error handling.
- `api-engineer`: Pydantic v2 models, async endpoints, structured logging
- `frontend-engineer`: TypeScript strict mode, React hooks for SSE, shadcn/ui components
- `ingestion-engineer`: Deterministic chunking, idempotent upserts, tombstone handling

### 5.3 Test
- Unit tests + integration tests + evaluation metrics
- `frontend-engineer`: Component tests + mock SSE stream tests
- `ingestion-engineer`: Chunk stability tests + idempotency tests + metadata completeness tests

### 5.4 Review
Self-review against REVIEW-STANDARDS.md standards.

### 5.5 Validate
CI pipeline must pass before completion.
- `pnpm check:structure` — layer boundary tests
- `pnpm test:api` — backend tests
- `pnpm test:ingestion` — ingestion pipeline tests
- `pnpm test:e2e` — Playwright e2e tests (includes frontend + backend integration)

