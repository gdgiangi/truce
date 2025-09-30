# Global Guardrails
- No breaking changes to public API without migration notes.
- Always add/adjust tests; explain failing cases and include a “How to verify” section.
- Include security checks (no API keys client-side, rate-limit external calls).
- Produce artifacts per task: `plan.md`, `changeset`, tests, and `FOLLOWUPS.md`.
- Keep replay bundles safe: redact secrets and cookies; store only needed metadata.
