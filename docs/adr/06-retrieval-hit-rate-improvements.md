# ADR-06: Retrieval Hit-Rate Improvements

## Status

Proposed — **one section below is intentionally left open** for a decision
before a coding agent starts implementation (see "Open Decision").

## Context

ARCHITECTURE.md §9.2 already defines the metrics that matter here:
Recall@k, Precision@k, MRR, and citation-source match rate, evaluated via
`docs/eval/eval_set.yaml` against `docs/eval/thresholds.yaml`. "Increase the
hit rate" is not a single change — it's a metric target, and this ADR names
the specific levers being pulled to move it, in the order they should be
applied and measured.

This ADR should land **after** ADR-04 (storage) and ADR-05 (multi-format
ingestion), because ADR-05 changes the chunk population (new
`document_type`, page-level metadata) enough that a hit-rate baseline
measured before it would not be comparable to one measured after.

## Baseline (must be captured before any change in this ADR ships)

Run `pnpm test:eval` against `main` immediately after ADR-05's re-ingestion
backfill completes, and record:

- Recall@8 (matches current `k=8` retrieval per ARCHITECTURE.md §6.2)
- Precision@8
- MRR
- citation-source match rate

These four numbers go in this ADR's "Results" section (append once measured)
and become the comparison point for every change below. No lever in this ADR
should be considered "done" without a before/after eval run.

## Decision: levers, in implementation order

### 1. Ticket search: substring match → PostgreSQL full-text search

**Problem:** ARCHITECTURE.md §3.1.1 step 4 currently does substring matching
("`subject` or `resolution` contains keywords from the query"), which misses
paraphrases and can both over- and under-match on common words.

**Change:** Add a `tsvector` generated column on `tickets` (combining
`subject` + `resolution`), a GIN index on it, and switch
`repositories/ticket.py`'s query method to `to_tsquery` /
`websearch_to_tsquery` ranked by `ts_rank`. This is a pure `repositories/`
change — no service-layer or router change needed, since the method
signature (`search_tickets(account_id, query) -> list[Ticket]`) stays the
same per CONVENTIONS.md's repository contract.

**Why first:** Lowest implementation risk, no new external dependency, and
isolated to one file — good first change to validate the before/after eval
workflow itself before touching riskier KB retrieval logic.

### 2. Reranking pass on top-k KB chunks

**Problem:** ARCHITECTURE.md §6.2 step 5 lists reranking as optional
("Optionally re-rank the combined set"). Vector similarity alone often
surfaces chunks that are topically close but not the most *directly*
relevant to answer the specific question.

**Change:** Retrieve a wider candidate set from Pinecone (e.g. `k=20` instead
of `k=8`), then rerank with a cross-encoder before truncating to the final
`k=8` used in prompt construction. This becomes a required step in
`services/chat.py`'s retrieval orchestration, not optional.

**Why second:** Directly targets Precision@k and citation-source match rate,
the two metrics most sensitive to "right document family, wrong specific
chunk" errors — the most common failure mode in KB-style RAG.

### 3. Query rewriting before embedding

**Problem:** User questions are often underspecified relative to how KB
docs are written (e.g. "replication won't start" vs. the doc's phrasing
"Enabling Replication for VMware VMs"). Embedding the raw query as-is misses
this vocabulary gap.

**Change:** Before generating the query embedding, pass the user's question
through a lightweight rewrite step (either a small/cheap LLM call, or a
simpler HyDE-style approach: generate a hypothetical answer snippet and embed
that instead of the raw question). This is additive to
`services/chat.py`'s existing flow — the rewritten query replaces
the raw query only for the embedding step; the raw query is still what's
shown to the user and still what's used for ticket full-text search from
lever 1.

**Why third:** Highest potential impact on Recall@k, but also the most
expensive (extra LLM round-trip adds latency) and the easiest to get wrong
(a bad rewrite can hurt more than help) — sequence it last so levers 1–2 are
already validated and isolated in the eval history before adding this
variable.

## Open Decision

**Scope for this iteration:** should all three levers ship together, or
should this be split into three separate PRs/ADR-06a/b/c, each with its own
before/after eval gate? Given ARCHITECTURE.md §9.5's release-gate rule ("no
change may regress citation correctness or groundedness"), shipping all
three at once makes it harder to attribute a regression to a specific lever
if the eval numbers move in an unexpected direction.

**Recommendation:** split into three sequential PRs in the order listed
above, each gated on its own eval run, rather than one combined change. If
you'd rather ship them together, say so explicitly and this ADR can be
updated to reflect a single combined rollout — but the eval-gate discipline
should still capture an intermediate measurement after lever 1 (ticket
search) before movement 2/3 are layered on top.

## Consequences

**Positive**

- Each lever is independently measurable against the same eval set, so a
  future regression can be attributed to a specific change rather than "the
  retrieval system got worse."
- Lever 1 has no new infra or model dependency and can ship fastest.

**Negative / follow-up work**

- Lever 2 (reranking) needs a reranker model choice (cross-encoder run
  locally vs. a hosted reranking API) — not decided in this ADR; note as a
  sub-decision when implementation starts.
- Lever 3 (query rewriting) adds latency (§9.4's p95/p99 targets should be
  re-checked after this lands, not just recall/precision).
- `docs/eval/eval_set.yaml` may need additional cases that specifically
  exercise paraphrase gaps (for lever 3) and ticket-search-only queries
  (for lever 1), since the current set may be weighted toward direct KB
  lookups.

## Related

- ADR-04 (MinIO storage), ADR-05 (multi-format ingestion) — must ship first;
  this ADR's baseline is measured against the post-ADR-05 chunk population.
