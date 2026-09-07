---
id: SPEC-002-project-bootstrap
requirement: REQ-WP-001
speckit_path: specs/002-project-bootstrap/spec.md
status: draft
---

## Summary

Provisions the local development stack and the repository's quality gate. One
command starts PostgreSQL and a MinIO object store; lint, type-check and test
commands pass green on a clean checkout; a Vite/React/TypeScript shell builds.

No analytical database is provisioned — see [[ADR-002]]. No application service
is containerised, and no schema is created; those arrive with the code that
needs them.

The authoritative text lives in the Spec Kit spec at `speckit_path`; this note
exists so the spec appears in the Obsidian graph.

## Links

- Requirement: [[REQ-WP-001]]
- Decision: [[ADR-002]]
