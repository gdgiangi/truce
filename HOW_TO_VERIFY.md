# How to Verify Agentic Research Updates

## Prerequisites
1. Set up Brave Search API key:
   ```bash
   export BRAVE_SEARCH_API_KEY=your_brave_api_key_here
   ```
2. Install FastMCP dependency:
   ```bash
   cd apps/adjudicator
   pip install -r requirements.txt
   ```

## Automated checks
1. Agentic research system tests:
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_agentic_research.py -v
   ```
   > Tests the multi-turn research flow, evidence collection, and shared evidence pool.

2. Traditional backend tests (cache + explorer pipeline):
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_explorer_agent.py tests/test_verification_cache.py
   ```
   > Full `pytest` runs may segfault locally due to optional native deps (pandas/scikit); the targeted suites cover the new caching and MCP explorer flows end-to-end.

3. Panel aggregation contract tests:
   ```bash
   cd apps/adjudicator
   python3 -m pytest tests/test_panel_aggregation.py tests/test_api_endpoints.py::TestPanelEndpoint::test_run_panel_returns_structured_payload
   ```
   > These suites validate the normalized prompt, provider fallbacks, panel summary math, and API wiring without requiring external API keys.

## Manual smoke tests

### Agentic Research Flow
1. Start the FastMCP Brave Search server:
   ```bash
   cd apps/adjudicator
   python3 -m truce_adjudicator.scripts.start_brave_server
   ```
   > Server should start on port 8000 and be available at http://localhost:8000/mcp

2. In a new terminal, start the main API server:
   ```bash
   cd apps/adjudicator
   MCP_BRAVE_SERVER_URL=http://localhost:8000/mcp uvicorn truce_adjudicator.main:app --reload --port 8001
   ```

3. In another terminal, start the web app:
   ```bash
   cd apps/web
   npm run dev
   ```

### Traditional Flow (Original)
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
   - You'll see a clean, minimalistic homepage with a prominent search bar
   - Enter any claim (e.g., "crime severity in Canada") in the search bar
   - Click "Search" — you should be immediately redirected to the `/analyzing` page with a minimalistic loading screen
   - Watch the progress indicators and animations as the system:
     * Searches for evidence
     * Gathers and processes sources
     * Evaluates with AI models
   - Upon completion, you'll be automatically redirected to the claim page (e.g., `/claim/crime-severity-in-canada`)
3. On the claim page (`/claim/[slug]`):
   - Verify that the "Evidence & Sources" section displays all gathered evidence with proper citations
   - Confirm the "Model Panel Evaluation" section shows detailed verdicts from each AI model with confidence levels and rationale
   - Check the sidebar "Model Consensus" widget displays the verdict distribution and support score
   - Each search creates a fresh analysis with real-time evidence gathering
4. Test the traditional multi-model panel aggregation directly via API:
   ```bash
   # First create a claim via the UI, then test the panel endpoint (traditional mode)
   curl -s -X POST \
     "http://localhost:8000/claims/crime-severity-in-canada/panel/run?agentic=false" \
     -H "Content-Type: application/json" \
     -d '{"models":["gpt-4o","grok-3","gemini-2.0-flash-exp","claude-sonnet-4-20250514"]}' | jq '.panel.summary'
   ```
   - Refresh the claim page and confirm the "Model Panel Evaluation" section shows per-provider cards with verdict badges, confidence bars, and citation callouts
   - The sidebar "Model Consensus" widget should mirror the summary verdict and confidence, and the support score should match the API response

### Agentic Research Testing
1. Test the new agentic research panel (requires both servers running):
   ```bash
   # Create a simple claim first
   curl -s -X POST "http://localhost:8001/claims" \
     -H "Content-Type: application/json" \
     -d '{"text":"Renewable energy adoption is accelerating globally","topic":"energy","entities":["renewable energy","global"]}' | jq '.slug'
   
   # Use the returned slug to test agentic research
   curl -s -X POST \
     "http://localhost:8001/claims/renewable-energy-adoption-is-accelerating-globally/panel/run?agentic=true" \
     -H "Content-Type: application/json" \
     -d '{"models":["gpt-4o","claude-sonnet-4-20250514"]}' | jq '.'
   ```
   - This should trigger independent research by each agent using the Brave API
   - Each agent will conduct 5 turns of research with different strategies
   - Sources will be deduplicated and shared across all agents
   - Final verdicts will be based on all collected evidence

2. Test agentic research with progress tracking:
   ```bash
   # Use Server-Sent Events to watch research progress
   curl -N -H "Accept: text/event-stream" \
     -X POST "http://localhost:8001/claims/renewable-energy-adoption-is-accelerating-globally/panel/agentic" \
     -H "Content-Type: application/json" \
     -d '{"models":["gpt-4o","claude-sonnet-4-20250514"]}'
   ```
   - You should see real-time progress updates showing:
     * Each agent starting independent research
     * Search strategies being executed (broad, perspective, targeted, gaps)
     * Evidence collection and deduplication
     * Verdict formation phase
     * Final aggregation results

3. Verify the Brave Search MCP server directly:
   ```bash
   # Test the web search tool
   curl -s -X POST "http://localhost:8000/mcp/tools/web_search" \
     -H "Content-Type: application/json" \
     -d '{"query":"climate change effects 2024","count":5}' | jq '.results | length'
   
   # Test multiple perspectives search
   curl -s -X POST "http://localhost:8000/mcp/tools/search_multiple_perspectives" \
     -H "Content-Type: application/json" \
     -d '{"claim":"renewable energy is becoming cost competitive"}' | jq '.perspectives | keys'
   ```
   - These should return search results from the Brave API
   - Multiple perspectives should include research, government, news, and expert viewpoints
5. (Optional) Test the verification API directly:
   ```bash
   # Use a claim slug from a previous search
   curl -s -X POST "http://localhost:8000/claims/crime-severity-in-canada/verify" | jq '.evidence_ids'
   ```
   Re-run with `force=true` query parameter and note that a new `verification_id` is issued while previously gathered evidence is reused (no duplicate URLs).
   
6. (Optional) Test async claim creation flow:
   ```bash
   # Create a new claim
   curl -s -X POST "http://localhost:8000/claims/create-async" \
     -H "Content-Type: application/json" \
     -d '{"query":"violent crime in Canada is rising"}' | jq '.'
   
   # Poll the session status (use session_id from previous response)
   curl -s "http://localhost:8000/claims/session/{session_id}" | jq '.'
   ```
   The session endpoint should show progress through: `searching`, `gathering`, `evaluating`, and finally `complete` with the claim slug.
