# M3 – Panel Aggregation & Per-Model Verdicts

## Goal
Run multiple providers on the same normalized prompt + evidence; aggregate.

## Acceptance Criteria
- Providers: OpenAI GPT-5, Grok, Gemini, Sonnet (stub ok).
- Normalized prompt schema: include claim text, time window, evidence snippets with source IDs.
- Parse outputs into:
{ provider_id, verdict: [true|false|mixed|unknown], confidence?:0..1, rationale, citations:[evidence_id] }
- Aggregation v1:
- Majority vote → panel verdict; ties → mixed
- Confidence = 1 - dispersion (e.g., 1 - (#disagree / #models))
- UI: per-model cards + panel summary bar; show citations.
- Tests: parsing edge cases; stable aggregation with same inputs.