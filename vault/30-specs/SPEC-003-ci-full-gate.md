---
id: SPEC-003-ci-full-gate
requirement: REQ-INFRA-002
speckit_path: specs/003-ci-full-gate/spec.md
status: draft
---

## Summary

Moves the checks that need live services out of the local pre-commit hook and
into a GitHub Actions workflow that provisions PostgreSQL and MinIO. The local
hook keeps lint, formatting and the non-integration tests; nothing is dropped
from both.

## Links

- Requirement: [[REQ-INFRA-002]]
