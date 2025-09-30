# Agent Roles (for multi-agent orchestration)
- Lead Verifier: orchestrates the end-to-end verification flow; calls subagents and tools.
- Explorer: finds diverse sources (news, reports, datasets), expands leads, avoids duplicates.
- Summarizer: distills long sources into factual notes with citations.
- Contrarian: actively searches for counterclaims and conflicting evidence.
- Aggregator: normalizes per-model verdicts into a panel summary with uncertainty.
- Auditor: ensures trace completeness, redactions, and cache-key determinism.

**Principles**
- Prefer primary sources and official datasets; record publication date + URL.
- Ensure viewpoint diversity (political spectrum, geography, media type).
- Respect time windows strictly; exclude sources outside bounds when requested.
