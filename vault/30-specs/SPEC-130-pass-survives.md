---
id: SPEC-130-pass-survives
requirement: REQ-INFRA-012
speckit_path: specs/130-pass-survives/spec.md
status: draft
---

## Summary

The worker and the resample job leave `main` when the first read of a pass raises: it happened twice on
2026-10-03 for unrelated causes (a snapshot race, an object-store 503). A pass that fails is now reported once
with its traceback, survived, and its recovery reported; `--once` still fails loudly and only `Exception` is
survived. Not a retry, not a backoff.

## Links

- Requirement: [[REQ-INFRA-012]]
- Built on: [[REQ-WP-073]], [[REQ-WP-077]]; finds from [[REQ-WP-079]], [[REQ-WP-081]]
