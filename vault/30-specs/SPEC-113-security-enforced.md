---
id: SPEC-113-security-enforced
requirement: REQ-WP-072
speckit_path: specs/113-security-enforced/spec.md
status: draft
---

## Summary

PRD §34 mostly holds today, and five of its eight requirements hold because
nobody has yet had the chance to break them: there are no logs, no write routes
and no CORS configuration. The spec turns each absence into a test that fails
when the absence ends, builds the one thing genuinely missing — rate limiting on
the public read API — and stops the stack publishing a database to whatever can
reach the host.

## Links

- Requirement: [[REQ-WP-072]]
