# How to Verify M1 Updates

## Automated checks
1. Backend cache & time-window tests
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_verification_cache.py
   ```
   > Note: running the full `pytest` suite may segfault in this environment because of optional native dependencies; the targeted suite above exercises the new verification cache logic end-to-end.

## Manual smoke tests
1. Start the API and web app (separate terminals):
   ```bash
   cd apps/adjudicator
   uvicorn truce_adjudicator.main:app --reload
   ```
   ```bash
   cd apps/web
   npm run dev
   ```
2. Visit `http://localhost:3000` and use the hero search bar. Enter a term such as “crime severity” to confirm `/search` results show both claim cards and evidence snippets.
3. Open the demo claim at `/claim/violent-crime-in-canada-is-rising`:
   - Adjust the start/end date pickers and observe the verification card re-run automatically.
   - Toggle “Refresh with latest” to confirm the cached badge disappears on a forced refresh and returns on subsequent runs.
   - Verify provider checkboxes affect the request (inspect network tab: `providers[]` query params change).
4. (Optional) Hit the API directly to inspect cache behaviour:
   ```bash
   curl -s -X POST "http://localhost:8000/claims/violent-crime-in-canada-is-rising/verify" | jq
   curl -s -X POST "http://localhost:8000/claims/violent-crime-in-canada-is-rising/verify?force=true" | jq
   ```
   Expect the second response to show `cached: false` with a new `verification_id`.
