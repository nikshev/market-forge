---
id: SPEC-029-setup-families
requirement: REQ-US-005
speckit_path: specs/029-setup-families/spec.md
status: draft
---

## Summary

PRD §31's `signals:` block as a unit a backtest can run. Both families already
existed as candidate shapes — the engine opens upper-zone shorts and middle-zone
shorts today — and what was missing was the family as configuration and as a
reported fact.

The restriction lives on the production `SignalMachine`, as `opens`, rather than
as a filter over a finished report. The engine tracks one candidate at a time, so
a middle-zone setup occupies the machine and the upper-zone setup two bars later
never opens; a filtered report would carry that interference in its counts while
looking clean. `opens=None` is every pair — what every caller before this had,
and what [[REQ-WP-010]]'s parity test compares against.

A family is data. A test asserts `families.py` holds no state, no transition and
no detector call: PRD §25.2 forbids a separate backtest implementation, and a
rule here would be a second engine with a nicer name.

## Links

- Requirement: [[REQ-US-005]]
- Builds on: [[REQ-WP-007]], [[REQ-WP-010]]
- Related: [[REQ-SCORE-001]] holds §31's `min_score`, which is not a family field
