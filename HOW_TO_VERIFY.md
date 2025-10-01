# How to Verify M1–M3 Updates

## Automated checks
1. Targeted backend tests (cache + explorer pipeline)
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_explorer_agent.py tests/test_verification_cache.py
   ```
   > Full `pytest` runs may segfault locally due to optional native deps (pandas/scikit); the targeted suites cover the new caching and MCP explorer flows end-to-end.
2. Panel aggregation contract tests
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_panel_aggregation.py tests/test_api_endpoints.py::TestPanelEndpoint::test_run_panel_returns_structured_payload
   ```
   > These suites validate the normalized prompt, provider fallbacks, panel summary math, and API wiring without requiring external API keys.

## Manual smoke tests
1. Start the API and web app in separate terminals:
   ```bash
   cd apps/adjudicator
   uvicorn truce_adjudicator.main:app --reload
   ```
   ```bash
   cd apps/web
   npm run dev
   ```
2. Visit `http://localhost:3000`:
   - Use the hero search bar to enter any claim (e.g., "crime severity in Canada").
   - Click "Search" — you should be immediately redirected to the `/analyzing` page with a minimalistic loading screen.
   - Watch the progress indicators and animations as the system:
     * Searches for evidence
     * Gathers and processes sources
     * Evaluates with AI models
   - Upon completion, you'll be automatically redirected to the claim page (e.g., `/claim/crime-severity-in-canada`).
3. On the claim page (`/claim/[slug]`):
   - Verify that the "Evidence & Sources" section displays all gathered evidence with proper citations.
   - Confirm the "Model Panel Evaluation" section shows detailed verdicts from each AI model with confidence levels and rationale.
   - Check the sidebar "Model Consensus" widget displays the verdict distribution and support score.
   - Note: The old verification controls have been removed for a cleaner, streamlined experience. Each search creates a fresh analysis.
4. Trigger the multi-model panel aggregation:
   ```bash
   curl -s -X POST \
     "http://localhost:8000/claims/violent-crime-in-canada-is-rising/panel/run" \
     -H "Content-Type: application/json" \
     -d '{"models":["gpt-5","grok-beta","gemini-2.0-flash","sonnet-stub"]}' | jq '.panel.summary'
   ```
   - Refresh the claim page and confirm the “Model Panel Evaluation” section shows per-provider cards with verdict badges, confidence bars, and citation callouts.
   - The sidebar “Model Consensus” widget should mirror the summary verdict and confidence, and the support score should match the API response.
5. (Optional) Inspect the verification API directly:
   ```bash
   curl -s -X POST "http://localhost:8000/claims/violent-crime-in-canada-is-rising/verify" | jq '.evidence_ids'
   ```
   Re-run with `force=true` and note that a new `verification_id` is issued while previously gathered evidence is reused (no duplicate URLs).
