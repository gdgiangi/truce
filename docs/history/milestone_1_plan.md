# Milestone M1 Implementation Plan

## Objectives
- Add SQLite FTS-backed search across claims and evidence.
- Implement time-window aware `/claims/{slug}/verify` endpoint with deterministic cache.
- Surface search UI, verification controls, and cache state in the Next.js frontend.
- Verify behaviour with automated tests and document verification steps.

## Workstreams

### 1. Backend data/index foundation
- Introduce lightweight SQLite module (e.g. `search_index.py`) to manage FTS5 tables for claims and evidence snippets.
- Extend claim/evidence lifecycle hooks to keep the FTS index in sync (claim creation, evidence ingestion, updates) while preserving current in-memory structures.
- Add shared utilities for normalizing claim text, computing evidence hashes, and generating cache keys.

### 2. Verification API + cache
- Define Pydantic models for verification requests/responses and a simple storage layer for verification results (UUIDs, verdicts, provider list, timestamps, cache flags).
- Implement `/search` and `/claims/{slug}/verify` endpoints:
  - `/search` queries FTS tables and returns ranked claim/evidence hits.
  - `/verify` filters evidence by time window, builds deterministic cache key, respects `force` flag, and returns cached vs. fresh results.
- Ensure evidence outside the requested window is ignored when computing verdicts and hashes.

### 3. Frontend integration
- Create search bar component + `/search` results page wired to the new API contract.
- Update claim page with date range pickers, provider multi-select or pills, “Refresh with latest” toggle, and “Cached ✓” badge when appropriate.
- Handle optimistic states (loading/error) minimally to keep UX responsive.

### 4. Quality + docs
- Add pytest coverage for cache hit/miss, force refresh, and time-window filtering behaviour (using FastAPI `TestClient`).
- Add frontend unit snapshot or interaction test if feasible (otherwise document gaps) and ensure existing suites keep passing.
- Update `HOW_TO_VERIFY.md` with commands for running backend/frontend tests and manual smoke checks; note any known limitations in `FOLLOWUPS.md`.

## Risks & Mitigations
- **FTS synchronization**: ensure index rebuild helpers can reset state during tests; expose `reset_index` utility.
- **Time parsing**: standardize ISO8601 parsing with timezone awareness to avoid off-by-one issues.
- **Deterministic hashing**: encapsulate normalization/hashing to prevent drift across callers.

## Definition of Done
- New endpoints return expected payloads and are covered by automated tests.
- Search UI and claim verification controls function against local API.
- `plan.md`, `HOW_TO_VERIFY.md`, tests, and `FOLLOWUPS.md` updated per guardrails.
