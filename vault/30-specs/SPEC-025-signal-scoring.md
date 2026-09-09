---
id: SPEC-025-signal-scoring
requirement: REQ-SCORE-001
speckit_path: specs/025-signal-scoring/spec.md
status: draft
---

## Summary

PRD §22's deterministic score, §22.4's explainability and §43's alert ranker —
extracted because [[REQ-US-001]] ("markets sorted by setup score") and
[[REQ-US-004]] ("contribution factors are shown") both need a score no
requirement covered.

Nothing here is derived. §22.1 gives the six groups and their caps, §22.2 a
worked example with every intermediate number, §22.3 the threshold and the words
"default research value only", §22.4 the five things an explanation stores, and
§43 the ranking formula. The spec quotes them.

The one judgement is [[ADR-044]]: §22.1 says a missing family "must not
automatically equal zero", and the two readings are to score it zero and flag
it, or to leave it out of the denominator. The second is taken, so a DeFi outage
lowers the confidence rather than costing ten points that would then be
indistinguishable from evidence against the setup.

## Links

- Requirement: [[REQ-SCORE-001]]
- Decision: [[ADR-044]]
- Feeds: [[REQ-US-001]], [[REQ-US-004]]
- Unblocks: [[ADR-016]]'s deferred score clause
