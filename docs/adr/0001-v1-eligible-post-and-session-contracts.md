# ADR 0001: v1 eligible-post and session contracts

- Status: Accepted
- Date: 2026-06-02
- Canonical code contract: `app.assistant.contracts.V1_ASSISTANT_CONTRACT`

## Context

Later indexing, retrieval, and chat API tasks need one stable v1 contract for what content
may be embedded and cited, when indexed content must be invalidated, and whether chat
session state is ephemeral or stored. This repository does not yet implement posts,
retrieval, embeddings, citations, or session persistence, so this ADR defines policy only.

## Decision

### Eligible posts

- The v1 source of truth is the current persisted post snapshot in the primary post store.
- Draft posts are not eligible for indexing, retrieval, prompts, or citations.
- Edit history is ignored in v1. Only the latest saved post body and current metadata are
  eligible for indexing.

### Invalidation and access checks

- The following events invalidate indexed content for v1:
  - post deletion
  - privacy reduction or any visibility change that removes the requester's access
  - moderation removal
  - block-related access loss
- At index time, invalidated content must be removed from the index or tombstoned so it
  cannot be retrieved for prompt assembly.
- At request time, retrieval consumers must re-check access before prompt assembly and
  citation generation. Deleted, private, moderated, or blocked content must be excluded
  even if stale index data still exists.

### Session persistence

- Session state is `ephemeral` in v1.
- v1 does not define a first-class persisted session object, transcript table, or durable
  server-side conversation state.
- Each request must therefore carry the context it needs, or rely on transient runtime state
  outside the product contract.

### Privacy and logging constraints

- Do not log raw embedding vectors.
- Do not log full prompt bodies.
- Do not log citation text; only log opaque identifiers and operational metrics needed for
  debugging.
- Do not retain private or deleted content outside the primary post store and the minimum
  operational index required to serve retrieval.

## Rationale

- Using the current persisted post snapshot avoids ambiguity when edits exist and matches the
  only stable content view downstream services can reliably read in v1.
- Excluding drafts and ignoring edit history minimizes privacy and consistency risk while the
  retrieval pipeline is still immature.
- Treating access loss as an invalidation event at both index time and request time protects
  against stale embeddings or stale retrieval hits leaking content.
- Keeping session state ephemeral avoids prematurely committing the system to transcript
  storage, retention, and deletion semantics before the product needs them.

## Consequences

- Later indexing work must enforce the eligibility rules at ingest time.
- Later retrieval and citation work must perform request-time access checks before assembling
  prompts or returning citations.
- If a future version needs persisted sessions, it must introduce a new ADR and add explicit
  storage, retention, and deletion behavior instead of changing this contract implicitly.
