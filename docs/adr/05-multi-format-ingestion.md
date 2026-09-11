# ADR-05: Multi-Format Knowledge Base Ingestion (PDF, DOCX)

## Status

Proposed

## Context

The ingestion pipeline (ARCHITECTURE.md §8) currently handles only Markdown
files from `docs/knowledge_base/`. The README's stated data flow
(§3.1.2.1) already claims support for "PDF, Word, .md," but no such parsing
exists today — this ADR is what makes that claim true.

Depends on ADR-04: source files are read from MinIO (by `storage_key`), not
from a repo path, once this ships.

## Decision

Add two new parsers alongside the existing Markdown parser, each normalizing
its format into the same intermediate representation before chunking, so
downstream chunking/embedding logic (ARCHITECTURE.md §8.3) stays
format-agnostic.

| Format | Library | Notes |
|---|---|---|
| `.md` | existing parser (unchanged) | Source of truth for the current 14 docs; no behavior change. |
| `.pdf` | `pypdf` | Text extraction only, page-by-page. Scanned/image-only PDFs (no extractable text layer) are explicitly **out of scope** for this iteration — see Consequences. |
| `.docx` | `python-docx` | Extracts paragraph text and heading styles; tables are extracted as flattened text (structured table extraction is out of scope for this iteration). |

### Intermediate representation

Each parser produces a list of `ParsedSection`:

```python
class ParsedSection(BaseModel):
    heading: str | None       # maps to existing `section_heading` metadata
    text: str
    page_number: int | None   # PDF only; None for md/docx
    order_index: int          # position within the document, for stable chunk ordering
```

The existing chunker (500 tokens / 50 overlap, ARCHITECTURE.md §8.3) operates
on the concatenated `ParsedSection` stream regardless of source format —
no format-specific chunking logic.

### New/changed metadata (extends ADR-04's additions to §1.1.1 / §8.4)

- `document_type` — one of `md` | `pdf` | `docx`. **Required field.** Per
  ARCHITECTURE.md §8.5, adding a required metadata field triggers
  re-embedding of *all* existing chunks — the 14 current Markdown docs must
  be re-ingested as part of this change's rollout, not just newly added
  files.
- `page_number` — populated for PDF chunks, `null` otherwise. Enables
  page-level citations for PDF sources (e.g. "see p. 4 of Disaster Recovery
  Runbook.pdf") instead of only document-level citation.

### Citation format change

`citation` SSE events (ARCHITECTURE.md §2) gain an optional `page_number`
field, populated only for PDF-sourced chunks. Frontend citation rendering
should display it when present ("Runbook.pdf, p. 4") and omit it otherwise —
this is additive and doesn't break existing MD/ticket citation rendering.

### New/changed service

Per CONVENTIONS.md's layering rules, parsers are pure functions with no
external SDK calls beyond the parsing library itself, and live under
`services/ingestion/parsers/` (one module per format: `markdown.py`,
`pdf.py`, `docx.py`), dispatched by file extension from
`services/ingestion/pipeline.py`. Reading the raw bytes from MinIO
(`repositories/storage.py`, per ADR-04) stays in the `services/` orchestration
layer, not inside the parsers themselves — parsers take `bytes` in and
`list[ParsedSection]` out, nothing else, so they're trivially unit-testable
without a running MinIO instance.

## Consequences

**Positive**

- Format-agnostic downstream pipeline — chunking, embedding, and Pinecone
  upsert code doesn't change at all.
- Page-level citations for PDFs improve answer traceability beyond what MD
  currently offers.

**Negative / explicitly out of scope for this iteration**

- **OCR is not included.** Scanned/image-only PDFs will extract as empty or
  near-empty text and should be rejected at ingestion time with a clear
  error (log + skip, don't silently upsert empty chunks) rather than
  ingested as garbage. If scanned-document support is needed later, that's
  a separate ADR (e.g. adding `pytesseract` or a hosted OCR API).
- **DOCX tables are flattened, not structured.** A table with meaningful
  row/column relationships will lose that structure in the chunked text.
  Acceptable for now given the KB's current content is mostly prose
  runbooks; revisit if table-heavy documents are added.
- **Re-ingestion of all 14 existing MD docs is required**, not optional,
  because `document_type` is a new required field (§8.5). This should be
  scheduled as a one-time backfill run alongside this change's deployment,
  and the eval suite (`docs/eval/eval_set.yaml`) should be run before and
  after to confirm no regression from the re-chunk.
- New dependencies: `pypdf`, `python-docx` added to
  `src/app/requirements.txt`.

## Related

- ADR-04 (MinIO source document storage) — source bytes for all formats are
  read from MinIO by this pipeline.
- ADR-06 (retrieval hit-rate improvements) — should be evaluated *after*
  this ADR ships and the re-ingestion backfill completes, so the hit-rate
  baseline reflects the new chunking population, not the old MD-only one.
