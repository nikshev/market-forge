---
id: SPEC-026-scored-markets
requirement: REQ-US-001
speckit_path: specs/026-scored-markets/spec.md
status: draft
---

## Summary

[[REQ-SCORE-001]]'s score reaching the surface: PRD §43's rank score orders the
market list, and §22.4's explanation travels with a signal's detail into a panel
that shows all six of §22.1's groups.

[[ADR-044]]'s distinction appears twice more here, both times where a reader
would otherwise see a number and no way to tell. An unscored market sorts after
every scored one and reports nulls rather than zeros — ranking it at zero would
place it among the worst setups and say it had been examined. A missing family
appears among the missing and never among the negative factors — "we have no
DeFi data" is not "the DeFi evidence is against this setup".

The explanation is deliberately not nested with the outcome. §27.4 requires the
later outcome "visually separated so it cannot be confused with information
available at signal time", and one object holding both would make that
impossible for any UI.

## Links

- Requirements: [[REQ-US-001]], [[REQ-US-004]]
- Builds on: [[REQ-SCORE-001]], [[REQ-API-001]], [[REQ-WP-009]]
- Decision carried: [[ADR-044]]
