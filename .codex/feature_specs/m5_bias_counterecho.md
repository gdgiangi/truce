# M5 – Bias / Provenance / Counter-echo

## Goal
Expose diversity, conflicts, and temporal drift to break echo chambers.

## Acceptance Criteria
- Compute per-verification metrics:
  - domain diversity index, geo diversity (by TLD or metadata), media type spread
- Contrarian subagent:
  - explicitly search for counterclaims; attach conflicting evidence; tag conflict pairs
- Temporal drift:
  - If median source age > X months or newer contradicts older, show “stale/changed” flag
- UI:
  - “Diversity score” pill; “Opposing evidence” panel; drift warnings
- Tests: metric calculations; drift detection triggers; conflict tagging.
