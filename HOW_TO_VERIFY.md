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
   - Use the hero search bar to query “crime severity” and confirm claim/evidence hits surface via `/search`.
3. Navigate to `/claim/violent-crime-in-canada-is-rising`:
   - Adjust the start/end date pickers and watch the verification controls re-run automatically.
   - Toggle “Refresh with latest” to force bypassing cache (`cached: false` should appear in the response before returning to cached on the next run).
   - Confirm the provider checkboxes update the `providers[]` query params in the network tab.
   - After a verify run, open the “Evidence & Sources” list and scroll to the latest entries — new items should show `provenance: mcp-explorer`, include titles, and reflect the current timestamp.
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
