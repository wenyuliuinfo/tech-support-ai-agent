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
src/api/                FastAPI backend API
src/services/           Python based backend business logic
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
- **Scope**: `src/api/`
- **Constraints**: OpenAPI 3.1 spec, Pydantic v2, async endpoints
- **Validation**: Above 80% endpoint test coverage required


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
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 5. Workflow: Feature Development
1. **Plan**: Agent analyzes task, references ARCHITECTURE.md & CONVENTIONS.md
2. **Implement**: Code with type hints, docstrings, error handling
3. **Test**: Unit tests + integration tests + evaluation metrics
4. **Review**: Self-review against REVIEW-STANDARDS.md standards
5. **Validate**: CI pipeline must pass before completion