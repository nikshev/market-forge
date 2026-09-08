---
id: SPEC-024-turning-derivative
requirement: REQ-WP-019
speckit_path: specs/024-turning-derivative/spec.md
status: draft
---

## Summary

The two acceptance criteria [[ADR-023]] left unmet, and Test F, which was
waiting on the same subsystems.

PRD §13A.13's direct target — §23.5A's Target E, already labelled by
[[REQ-WP-017]] — is scored fold by fold against the no-skill base rate. That is
REQ-WP-019's fourth condition, "direct baseline metrics exist", and the
comparison rather than the score is the point: a Brier number alone reads like a
result.

PRD §13A.11's forward path is fitted with [[REQ-WP-018]]'s GMDH, one network per
coefficient, and the horizons where its derivative is zero become candidates.
§13A.12's gate then decides whether any may be promoted, over a deterministic
perturbation lattice ([[ADR-041]]) — which is [[REQ-NRT-F]], Test F, whose
subject is a root that "can appear from tiny coefficient changes".

The experiment returns `NO_EDGE` rather than raising it ([[ADR-042]]): a
research result that raises is a research result that blocks, and that coupling
is exactly what REQ-WP-019's fifth condition asks to be removed. A mistake in
the call still raises, so an absence of edge is never reported for a hypothesis
that was never actually tested.

## Links

- Requirements: [[REQ-WP-019]], [[REQ-NRT-F]]
- Decisions: [[ADR-041]], [[ADR-042]], [[ADR-043]], supersedes [[ADR-023]] on this point
- Builds on: [[REQ-WP-017]], [[REQ-WP-018]]
