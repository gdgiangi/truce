# Follow-ups
- Investigate why running the full `python3 -m pytest` suite segfaults in this environment (likely pandas/scikit native deps); prefer a containerised run so broader regression coverage can pass.
- Add frontend unit tests (e.g., React Testing Library) for the new search results page and `ClaimVerifier` interactions once a testing harness is in place.
- Persist verification records (instead of in-memory cache) if multi-process deployment is required, and surface historical runs on the claim page.
- Extend `/search` relevance scoring to include highlights/snippets and pagination for large result sets.
- Wire the MCP explorer to live tool backends (web search, link expansion) and add configuration for API keys / rate limits once available.
- Move explorer-gathered evidence into durable storage (SQLite/Postgres) with provenance audit logs rather than in-memory claim structs.
- Surface domain diversity diagnostics in the UI so reviewers know when sources were dropped due to concentration limits.
- Replace the stubbed Grok/Gemini/Sonnet adapters with real client integrations once API credentials are provisioned and confirm JSON contract parity across providers.
- Add a front-end action to trigger `/claims/{slug}/panel/run` from the claim page so reviewers can refresh model verdicts without manual curls.
