---
id: SPEC-014-turning-points
requirement: REQ-WP-019
speckit_path: specs/014-turning-points/spec.md
status: draft
---

## Summary

PRD §13A.30's step 2: the directional-change swing baseline, with §13A.1's two
timestamps — `extremum_time` for when the price made the high, `known_at` for
when the system could first legally say so — and §13A.28's five buildable
non-repainting tests.

Those five tests are this repository's only `hard_gated` requirements that have
never had a home. [[ADR-022]] explains Test D's shape: the PRD says the
production path fails when a transform *declares* centered future dependence,
so transforms declare and the engine refuses, with a source check beside it and
Test A as the backstop against a false declaration.

[[ADR-023]] records why [[REQ-WP-019]] stops at `tested`: two of its five
acceptance criteria need [[REQ-WP-017]]'s dataset and [[REQ-WP-018]]'s GMDH,
and Principle IV forbids both until the deterministic baseline this feature
builds has passed its leakage tests.

## Links

- Requirements: [[REQ-WP-019]], [[REQ-NRT-A]], [[REQ-NRT-B]], [[REQ-NRT-C]], [[REQ-NRT-D]], [[REQ-NRT-E]]
- Decisions: [[ADR-022]], [[ADR-023]]
- Consumes: [[REQ-WP-005]], [[REQ-WP-006]]
- Blocked on: [[REQ-WP-017]], [[REQ-WP-018]] for the rest of REQ-WP-019
