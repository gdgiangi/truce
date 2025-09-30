# Milestone M2 Implementation Plan

## Objectives
- Provide an MCP Explorer pipeline that gathers ≥8 diverse, time-relevant sources before verification.
- Persist gathered sources as normalized Evidence entries while avoiding duplicates and domain concentration.
- Hook the explorer into the `/claims/{slug}/verify` flow so models receive freshly gathered evidence.
- Cover the pipeline with automated tests and document verification steps.

## Workstreams

### 1. Explorer toolchain foundation
- Implement an MCP toolset module exposing `search_web`, `fetch_page`, `expand_links`, and `deduplicate_sources` APIs (stubbed but structured for mocking).
- Create an `ExplorerAgent` orchestrator that chains the tools, normalizes URLs/domains, applies time-window filters, and enforces the ≤40% per-domain rule.
- Extend Evidence modeling to capture title, domain, and retrieved timestamps required by the spec.

### 2. Verification pipeline integration
- Integrate the explorer within `/claims/{slug}/verify` so gathering runs before cache evaluation, reuses deterministic keys, and persists new evidence when not already attached.
- Plug gathered evidence into the existing search index and claim structures while maintaining deduplication by normalized URL / content hash.

### 3. Quality gates & docs
- Add pytest coverage for tool-call sequencing (mocked), evidence persistence, and domain diversity enforcement.
- Update `HOW_TO_VERIFY.md` with backend/frontend steps for the explorer flow and cache interactions.
- Capture any deferred improvements in `FOLLOWUPS.md`.

## Risks & Mitigations
- **Duplicate handling**: Normalize URLs and hash snippets to avoid re-adding the same source; add unit tests.
- **Domain diversity**: Compute per-domain caps and surface diagnostics in tests to ensure enforcement.
- **Test brittleness**: Structure explorer dependencies for dependency injection to simplify mocking without touching global state.

## Definition of Done
- MCP tool module + explorer agent functional with ≥8 unique sources and diversity guardrail.
- `/verify` endpoint gathers and persists evidence prior to cache hit checks, updating search index as needed.
- Automated tests green; `HOW_TO_VERIFY.md` and `FOLLOWUPS.md` updated with M2 context.
