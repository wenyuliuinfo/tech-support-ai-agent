# v2 Iteration: Storage, Multi-Format Ingestion, Retrieval Hit-Rate

This document sequences ADR-04, ADR-05, and ADR-06 for implementation. Give
this file to the coding agent alongside `AGENTS.md`, `CONVENTIONS.md`, and
`ARCHITECTURE.md` — it assumes all three as background and doesn't repeat
their content.

## Why order matters here

These three changes are not independent:

- ADR-05 (multi-format ingestion) needs ADR-04 (MinIO storage) shipped first
  — PDF/DOCX files need a place to land before they can be parsed.
- ADR-06 (hit-rate improvements) needs to be measured against the
  post-ADR-05 chunk population (new `document_type` field triggers
  re-embedding of everything, per ARCHITECTURE.md §8.5) — measuring a
  "before" baseline prior to ADR-05 would not be comparable to the "after."

Implementing them out of order means re-doing eval baselines and possibly
re-ingesting twice. Follow the sequence below.

## Sequence

### Phase 1 — ADR-04: MinIO storage

1. Add MinIO service to `infra/docker-compose.yml`.
2. Add `repositories/storage.py` (upload/get/list/archive methods).
3. Add `.env.example` entries: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`,
   `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME`.
4. Add `storage_key` / `storage_bucket` to Pinecone chunk metadata (additive
   fields — does not require re-embedding on its own, since existing
   required fields are unchanged).
5. One-time migration script: backfill the 14 existing `docs/knowledge_base/*.md`
   files into MinIO as version 1, so all documents are addressable via
   `storage_key` going forward.
6. Update `ARCHITECTURE.md` §8.1 and §1.1.1 to name MinIO as canonical
   source-of-truth for document content (git remains provenance for the
   original 14 files only).

**Definition of done:** `pnpm test:api` passes with a new
`test_storage_repository.py`; the 14 existing docs are retrievable from
MinIO by `storage_key`; ingestion still works unchanged (this phase doesn't
touch the parser or chunker).

### Phase 2 — ADR-05: multi-format ingestion

1. Add `pypdf`, `python-docx` to `src/app/requirements.txt`.
2. Add `services/ingestion/parsers/{markdown,pdf,docx}.py`, each producing
   `list[ParsedSection]`.
3. Add `document_type` (required) and `page_number` (optional, PDF-only) to
   Pinecone chunk metadata.
4. Update `citation` SSE event schema to carry optional `page_number`
   (ARCHITECTURE.md §2) and update frontend `ChatPanel` citation rendering
   to display it when present.
5. **Re-ingest all existing documents** (required, since `document_type` is
   a new required field — ARCHITECTURE.md §8.5) via the migrated MinIO
   copies from Phase 1.
6. Add at least 2–3 PDF and 2–3 DOCX documents to the KB (real or
   test-fixture content) and corresponding eval cases in
   `docs/eval/eval_set.yaml` that specifically target them, so format
   coverage is asserted, not assumed.
7. Reject (log + skip, don't upsert) any file that yields empty/near-empty
   extracted text (guards against silently ingesting scanned/image-only
   PDFs, which are explicitly out of scope per ADR-05).

**Definition of done:** `pnpm test:eval` passes including new PDF/DOCX eval
cases; `pnpm ingest` run against the full KB (14 MD + new PDF/DOCX fixtures)
completes without errors; citation events show `page_number` for PDF-sourced
answers.

### Phase 3 — ADR-06: retrieval hit-rate improvements

**Before starting:** run `pnpm test:eval` against the Phase 2 result and
record Recall@8, Precision@8, MRR, and citation-source match rate in ADR-06's
"Results" section. This is the comparison baseline for everything below.

1. Ticket search: substring match → PostgreSQL full-text search
   (`repositories/ticket.py` only). Run eval; record delta.
2. Reranking pass on KB retrieval (`services/chat.py`). Run eval;
   record delta.
3. Query rewriting before embedding (`services/chat.py`). Run eval;
   record delta; also re-check p95/p99 latency (ARCHITECTURE.md §9.4) since
   this lever adds a round-trip.

Ship each numbered item as its own PR with its own eval run attached, per
ADR-06's "Open Decision" recommendation — don't combine 1–3 into a single
commit.

**Definition of done:** each lever has a recorded before/after eval delta in
ADR-06; no lever regresses citation correctness or groundedness beyond
`docs/eval/thresholds.yaml` (ARCHITECTURE.md §9.5); overall Recall@8 and
citation-match rate improve versus the Phase 2 baseline.

## Files to prepare before handing this to a coding agent

| File | Status | Purpose |
|---|---|---|
| `docs/adr/04-source-document-storage.md` | drafted | MinIO decision |
| `docs/adr/05-multi-format-ingestion.md` | drafted | PDF/DOCX parsing decision |
| `docs/adr/06-retrieval-hit-rate-improvements.md` | drafted, one open decision | Hit-rate levers |
| `docs/adr/CHANGELOG-v2.md` | this file | Sequencing across all three |
| `ARCHITECTURE.md` | needs edits *during* each phase, not upfront | §1.1.1, §3.1.2.1, §6.2, §8 |
| `CONVENTIONS.md` | needs one edit | add `boto3`/MinIO SDK and `pypdf`/`python-docx` to the "repositories-only" external SDK list |
| `.env.example` | needs edits in Phase 1 | MinIO credentials |
| `docs/eval/eval_set.yaml` | needs new cases in Phase 2 and 3 | PDF/DOCX cases; paraphrase/ticket-search cases |
| `docs/eval/thresholds.yaml` | review after Phase 3 baseline | may need updated targets once ADR-06 lands |

Do not pre-edit `ARCHITECTURE.md` or `CONVENTIONS.md` in one big pass before
coding starts — edit each section as its corresponding phase lands, so the
docs never describe a state the code hasn't reached yet.
