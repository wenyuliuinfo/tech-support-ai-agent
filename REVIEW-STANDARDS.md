# Review Standards

This file defines the working standards for coding agents in this repository.
Use it together with `AGENTS.md`, `CONTEXT.md`, `ARCHITECTURE.md`, and `CONVENTIONS.md`.

## Purpose

This repository builds a tech-support RAG system that answers user questions using:
- Knowledge Base Documents from `docs/knowledge_base`
- account-scoped ticket history from PostgreSQL
- a FastAPI backend and Next.js frontend

Agents should optimize for grounded answers, simple implementations, and safe handling of customer data.

## Read Order

Before making changes, read documents in this order:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `ARCHITECTURE.md`
4. relevant ADRs in `docs/adr/`
5. `CONVENTIONS.md`
6. `REVIEW-STANDARDS.md`

## Core Rules

- Do not invent product behavior that is not supported by retrieved documentation.
- Treat Knowledge Base Documents as the primary grounding source.
- Treat historical tickets as secondary context only.
- Scope ticket access by `account_id`.
- Keep designs and code aligned with the documented architecture.
- Prefer the simplest implementation that satisfies the current requirement.
- Do not add speculative abstractions.

## What Good Changes Look Like

A good change in this repo:

- respects the domain language in `CONTEXT.md`
- follows the architectural constraints in `ARCHITECTURE.md`
- preserves retrieval grounding and citation behavior
- includes tests for the changed behavior
- includes observability and error handling where relevant
- does not quietly expand scope

## RAG-Specific Expectations

When changing retrieval, prompting, ingestion, or evaluation logic:

- explain the change in terms of grounding quality and failure modes
- state how citations are preserved or improved
- describe any impact on latency or cost
- add or update evaluation coverage where possible
- do not let Ticket Context override Knowledge Base guidance unless explicitly designed

## API Expectations

When changing APIs:

- keep request and response schemas explicit
- validate inputs with Pydantic v2
- use async I/O throughout
- define error behavior clearly
- preserve streaming semantics for chat endpoints if applicable

## Data Expectations

When changing data models or ingestion:

- define the source of truth
- avoid duplicate fields unless there is a clear reason
- make chunk IDs and ingestion behavior deterministic
- document schema changes in `ARCHITECTURE.md` or an ADR if the decision is hard to reverse

## Security Expectations

- never expose secrets in code
- sanitize and validate user input
- avoid storing unnecessary PII
- ensure account-scoped data stays account-scoped
- treat retrieved content as untrusted input

## Review Checklist

Before considering work complete, check:

- Is the terminology consistent with `CONTEXT.md`?
- Is the change consistent with `ARCHITECTURE.md` and ADRs?
- Is the scope minimal?
- Are tests included or updated?
- Are failure cases handled appropriately?
- Is the retrieval behavior still grounded and explainable?
- Are security and access boundaries preserved?

## Done Criteria

A task is done when:

- the requested behavior is implemented
- tests for the changed behavior pass
- the architecture and domain docs remain consistent
- no undocumented architectural drift was introduced

## Non-Goals

Agents should not:

- redesign unrelated parts of the codebase
- add new infrastructure without documenting the decision
- introduce flexible frameworks for one-off needs
- silently change domain language or retrieval policy

## When To Write An ADR

Create or update an ADR when the change is:

- hard to reverse
- surprising without context
- based on a real tradeoff

Examples:
- changing retrieval strategy
- changing vector store or database choice
- changing tenant/data isolation rules
- changing ingestion/versioning policy