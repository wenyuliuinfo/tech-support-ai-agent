# ADR-04: Self-Hosted MinIO for Source Document Storage

## Status

Proposed

## Context

Today, `docs/knowledge_base/*.md` is the sole source of truth for Knowledge Base
content: files live in git, and the ingestion pipeline reads them directly from
the repo checkout before chunking and embedding into Pinecone (ARCHITECTURE.md
§8.1). Pinecone metadata stores `source_path` as a repo-relative path
(ARCHITECTURE.md §1.1.1).

This breaks down once source documents include binary formats (PDF, DOCX — see
ADR-05) and once documents may be uploaded outside of a git commit (e.g. by a
support-content editor, not a developer). Git is not a good fit for binary
asset storage or for a non-developer upload workflow, and Pinecone was never
meant to hold anything but vectors + text metadata.

## Decision

Introduce a self-hosted **MinIO** instance as the canonical object store for
all source documents (`.md`, `.pdf`, `.docx`). MinIO is chosen because:

- S3-compatible API — the ingestion pipeline and any future tooling can use
  the standard `boto3` (or `aioboto3` for async) client rather than a bespoke
  SDK.
- Self-hosted — no new external vendor dependency, consistent with running
  Postgres and Pinecone-emulator locally today (`infra/docker-compose.yml`).
- Runs alongside the existing `infra/` docker-compose stack with minimal
  operational overhead for a project this size.

### Bucket layout

```
tech-support-kb/
├── knowledge-base/
│   └── {document_id}/{ingestion_version}/{file_name}
└── _archive/
    └── {document_id}/{ingestion_version}/{file_name}   # tombstoned versions
```

- `document_id` matches the existing Pinecone metadata field (ARCHITECTURE.md
  §1.1.1) — MinIO key and vector metadata are joined on this field, not on
  filename, since filenames can collide or be renamed.
- Every re-upload of the same logical document creates a new
  `ingestion_version` key rather than overwriting in place, so a bad upload
  can be rolled back and prior versions remain retrievable for audit
  (ADR-03's idempotency guarantee extends naturally to this layout).
- Deleted documents move to `_archive/` rather than being hard-deleted,
  mirroring the existing Pinecone tombstone behavior (ARCHITECTURE.md §8.2
  step 6).

### Data model changes

Add to Pinecone chunk metadata (ARCHITECTURE.md §1.1.1 / §8.4):

- `storage_key` — the MinIO object key for the source file this chunk was
  extracted from.
- `storage_bucket` — bucket name (kept explicit rather than hardcoded, to
  support a future multi-bucket or multi-environment setup).

`source_path` is retained for backward compatibility with existing chunks and
for human-readable display in citations, but is no longer assumed to be a
filesystem-resolvable path once MinIO is live — only `storage_key` is.

### Source of truth

MinIO becomes the source of truth for document *content*. Git continues to
track document *provenance for the initial 14 Markdown files only* — new
uploads (of any format) go directly to MinIO and are not required to also
land in git. This is a deliberate change from ARCHITECTURE.md §8.1's current
"the source of truth is the `docs/knowledge_base` directory in the
repository," and that section must be updated to reflect MinIO as canonical
once this ADR ships.

### New repository

Per CONVENTIONS.md's layering rule (external SDKs live only in
`repositories/`), add `repositories/storage.py` wrapping the MinIO/S3 client
with plain async methods: `upload(key, content, content_type) -> StorageObject`,
`get(key) -> bytes`, `list(prefix) -> list[StorageObject]`, `archive(key)`.
No other layer imports `boto3` or the MinIO SDK directly.

## Consequences

**Positive**

- Binary and text source files have a consistent home, decoupled from git and
  from Pinecone.
- Versioned keys give a natural audit trail and rollback path.
- S3-compatible API means the storage backend can be swapped later (e.g. to
  real S3 in production) by changing only `repositories/storage.py`.

**Negative / follow-up work**

- New operational dependency: MinIO needs to be added to
  `infra/docker-compose.yml`, backed up, and access-controlled (bucket
  policy, credentials in `.env` / secrets manager per CONVENTIONS.md's
  security section).
- `ARCHITECTURE.md` §8.1 and §1.1.1 need updating once this ships.
- Existing 14 Markdown documents should be backfilled into MinIO (as version
  1) so all documents — old and new — are addressable the same way; this is
  a one-time migration script, not part of the standard ingestion CLI.
- New env vars required: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`,
  `MINIO_SECRET_KEY`, `MINIO_BUCKET_NAME` — add to `.env.example`.

## Related

- ADR-03 (Knowledge Base ingestion versioning) — this ADR extends the same
  versioning philosophy to the storage layer.
- ADR-05 (multi-format ingestion) — depends on this ADR; PDF/DOCX files need
  somewhere to land before they can be parsed.
