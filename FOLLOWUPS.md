# Follow-ups
- Investigate why running the full `python3 -m pytest` suite segfaults in this environment (likely pandas/scikit native deps); prefer a containerised run so broader regression coverage can pass.
- Add frontend unit tests (e.g., React Testing Library) for the new search results page and `ClaimVerifier` interactions once a testing harness is in place.
- Persist verification records (instead of in-memory cache) if multi-process deployment is required, and surface historical runs on the claim page.
- Extend `/search` relevance scoring to include highlights/snippets and pagination for large result sets.
