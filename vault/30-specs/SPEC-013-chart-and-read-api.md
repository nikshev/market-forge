---
id: SPEC-013-chart-and-read-api
requirement: REQ-WP-009
speckit_path: specs/013-chart-and-read-api/spec.md
status: draft
---

## Summary

PRD §28's read API and §27's chart, specified together because neither is
testable alone. The property that matters is that an alert's deep link opens
the instant it names showing the channel **as it stood then** — §27.5's
`AS-SEEN-THEN`, which the PRD calls critical because it "directly exposes
repaint-like differences".

[[ADR-019]] gives the API a repository port instead of a database, since PRD
§29's storage is unbuilt. [[ADR-020]] makes `AS-SEEN-THEN` the default
everywhere and requires the chart to state which mode it is in — an unlabelled
chart is worse than either mode, because a reader who cannot tell will read a
refit as evidence. [[ADR-021]] puts the frontend's checks in CI rather than in
the pre-commit hook.

## Links

- Requirements: [[REQ-API-001]], [[REQ-WP-009]]
- Decisions: [[ADR-019]], [[ADR-020]], [[ADR-021]]
- Consumes: [[REQ-WP-005]], [[REQ-WP-006]], [[REQ-WP-007]], [[REQ-WP-011]]
- Completes: [[REQ-WP-008]]'s deep link target
