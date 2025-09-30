# M4 – Replay Bundles (Per-Model)

## Goal
Record a complete, per-model replay of the verification process, downloadable.

## Acceptance Criteria
- Trace recorder captures:
  - timestamps, prompts, tool calls (MCP), responses, chosen evidence IDs, decisions
- Store JSON per provider under the Verification ID.
- Export endpoint:
  - `GET /verifications/{id}/replay?model=provider_id` → zip {trace.json, pretty.html, assets/*}
- Redact: API keys, cookies, PII.
- UI: “View Trace” modal (collapsible steps) + “Download Bundle”.
- Tests: completeness (required fields present), redactions applied, deterministic IDs.
