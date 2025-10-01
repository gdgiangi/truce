# Follow-ups

## Completed ✅
- ✅ **Fixed Claude model**: Updated deprecated `claude-3-5-sonnet-20241022` to `claude-sonnet-4-20250514`
- ✅ **Enhanced evidence gathering**: Increased from 8 to 20 sources with no timeout restrictions
- ✅ **Improved source diversity**: Reduced domain share from 40% to 25% for more varied perspectives
- ✅ **Multiple search strategies**: Added academic, government, news, and direct search approaches
- ✅ **Expanded domain recognition**: Added 50+ Canadian and international credible sources
- ✅ **Removed timeout constraints**: Evidence gathering now takes the time needed for comprehensive results
- ✅ **Agentic loading UI**: Replaced progress bars with real-time agent activity feed
- ✅ **Agent reasoning display**: Shows live agent thoughts and decision-making process
- ✅ **Graceful error handling**: No fallbacks - transparent error reporting with detailed messages
- ✅ **Multi-agent dashboard**: Live overview of active agents and evidence discovered

## High Priority 🔥
- **CRITICAL: Configure BRAVE_SEARCH_API_KEY with AI Grounding Plan** - Evidence gathering requires Brave AI Grounding API subscription. Without this, searches will return 0 sources (as shown in terminal logs). Get key from: https://api-dashboard.search.brave.com/
- Add ability to cancel in-progress analysis from the analyzing page (DELETE endpoint integration).
- Implement analysis history/bookmarking so users can revisit previous analyses without recreating them.
- Add estimated time remaining indicator on analyzing page based on average completion times.
- Consider adding retry logic for failed analyses with exponential backoff.

## Medium Priority 📋
- Add frontend unit tests (e.g., React Testing Library) for the new analyzing page and streamlined search flow once a testing harness is in place.
- Surface domain diversity diagnostics in the UI so reviewers know when sources were dropped due to concentration limits.
- Evaluate whether to completely remove `/search` page or repurpose it for browsing existing claims.
- Add search result quality scoring based on source credibility and relevance.

## Low Priority / Infrastructure 🔧
- Investigate why running the full `python3 -m pytest` suite segfaults in this environment (likely pandas/scikit native deps); prefer a containerised run so broader regression coverage can pass.
- Wire the MCP explorer to live tool backends (web search, link expansion) and add configuration for API keys / rate limits once available.
- Move explorer-gathered evidence into durable storage (SQLite/Postgres) with provenance audit logs rather than in-memory claim structs.
- Replace the stubbed Grok/Gemini/Sonnet adapters with real client integrations once API credentials are provisioned and confirm JSON contract parity across providers.
- Add geographical diversity preferences (Canadian vs international sources balance).
