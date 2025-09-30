# M1 – Core: Search, Time Window, Deterministic Cache

## User Stories
- As a user, I can search claims/evidence quickly.
- I can verify a claim for a specific time window.
- I see when a result is served from cache, and I can force refresh.

## Acceptance Criteria
- `GET /search?q=` returns hits from claims and evidence (FTS5 ok).
- `POST /claims/{slug}/verify?time_start&time_end&providers[]&force`:
  - Construct cache key from: SHA256(normalized_claim_text | time_start | time_end | sorted_providers | sources_hash)
  - On cache hit: return `{cached:true, verification_id, verdict, created_at}`
  - On `force=true`: bypass cache and create a new verification
- UI:
  - SearchBar in web app + results page.
  - Claim page: date range pickers; “Refresh with latest” toggle; “Cached ✓” badge.
- Tests:
  - Cache hit after first run.
  - Force refresh creates new verification.
  - Time window excludes evidence outside bounds.
