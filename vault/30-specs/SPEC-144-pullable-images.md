---
id: SPEC-144-pullable-images
requirement: REQ-INFRA-013
speckit_path: specs/144-pullable-images/spec.md
status: draft
---

## Summary

The two MinIO images the stack and CI pin can no longer be pulled by anyone but a machine that cached them.
Replace them with a pullable, drop-in build pinned by tag and index digest, make compose and CI name the same
one, and add a check that asks every registry whether every named image still resolves, run in CI before the
first pull. The authoritative text lives in the Spec Kit spec at `speckit_path`.

## Links

- Requirement: [[REQ-INFRA-013]]
- Follows: [[ADR-064]]
