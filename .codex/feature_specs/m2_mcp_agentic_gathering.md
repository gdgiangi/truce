# M2 – MCP & Agentic Source Gathering (Explorer v1)

## Goal
Before verification, gather diverse, time-appropriate sources via MCP tools.

## Acceptance Criteria
- Implement MCP server exposing:
  - `search_web`, `fetch_page`, `expand_links`, `deduplicate_sources`
- Lead Verifier → Explorer subagent flow:
  - Input: claim text + optional time window
  - Output: N (>=8) unique sources with metadata (title, url, domain, published_at, retrieved_at)
- Persist sources as Evidence rows; deduplicate by normalized URL / content hash.
- Diversity heuristic: enforce max share from any single domain (e.g., ≤40%).
- Integrate into /verify pipeline (gather → persist → pass to models).
- Tests:
  - Mock tool calls; persistence validated.
  - Diversity rule triggers when results are too concentrated.
