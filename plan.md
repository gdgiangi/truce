# Plan – M3 Panel Aggregation

## Objectives
- Support provider adapters for GPT, Grok, Gemini, and a Sonnet stub while keeping real API calls optional.
- Normalize the panel prompt (claim, time window, evidence IDs/snippets) and parse provider responses into a strict schema.
- Aggregate per-model verdicts through majority vote with dispersion-based confidence, persisting results for the claim.
- Expose panel data via the API and surface per-model cards plus a panel summary in the web UI.
- Cover parsing edge cases and aggregation stability with targeted tests, and document verification steps.

## Implementation Steps
1. **Model & Prompt Schema**
   - Add panel verdict enums and result models (provider verdict + panel summary) to `truce_adjudicator.models`.
   - Implement a normalized prompt builder (JSON payload: claim text, time window, evidence metadata) reusable by adapters.

2. **Provider Adapters**
   - Introduce adapter classes for GPT (OpenAI), Grok, Gemini, and a deterministic Sonnet stub.
   - Each adapter accepts the normalized prompt, handles missing API keys by falling back to mock outputs, and parses structured responses into the new model schema.

3. **Aggregation Pipeline**
   - Implement a panel runner that uses adapters, collects `PanelModelVerdict` entries, and computes a summary via majority vote (ties → mixed) with confidence `1 - (#disagree / #models)`.
   - Persist the latest panel result on the claim, update existing `ModelAssessment` entries for compatibility, and adjust `/claims/{slug}/panel/run` to return the structured payload.

4. **Frontend Updates**
   - Extend the claim page to consume the new panel summary + per-model verdicts, render provider cards (including Grok/Gemini/Sonnet), and show citations.
   - Ensure the panel UI gracefully handles missing data and highlights the majority verdict/confidence bar.

5. **Testing & Docs**
   - Add backend unit tests for prompt generation, adapter parsing fallbacks, and aggregation determinism.
   - Update or replace existing API tests mocking `create_mock_assessments` to align with the new panel result shape.
   - Add/adjust frontend tests for the panel components if feasible (or document follow-ups if harness lacking).
   - Refresh `HOW_TO_VERIFY.md` with steps covering the panel workflow.

## Risks & Mitigations
- **External API variability**: use mocks/deterministic fallbacks to keep tests offline.
- **Breaking existing assessments**: map new verdict enums to legacy `VerdictType` to maintain downstream behaviour.
- **UI regression**: keep old data paths until new ones are in place; gate rendering on presence of panel payload.

## Validation
- Targeted pytest suite covering panel aggregation modules.
- Manual check of `/claims/{slug}/panel/run` response and the updated claim page with mock data.
