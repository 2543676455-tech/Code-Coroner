# Contributor Agent Notes

- Keep conclusions evidence-based. Never invent repository behavior or test results.
- Never execute analyzed repository code on the host. Use `services/sandbox.py`.
- Preserve URL validation, file-size limits, path containment, and secret redaction.
- Add a deterministic test for every scanner or scoring rule change.
- The LLM may explain supplied evidence but must not create evidence or control more than 10 score points.
