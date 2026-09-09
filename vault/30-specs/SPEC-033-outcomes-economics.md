---
id: SPEC-033-outcomes-economics
requirement: REQ-BT-001
speckit_path: specs/033-outcomes-economics/spec.md
status: draft
---

## Summary

PRD §40's outcome definitions, §25.4's phase-1 fills and §25.5's metrics — the
three things [[ADR-009]] named as the condition for a backtest to report returns
at all.

§40's own emphasis is the design: "never choose the favorable ordering". A bar
whose range contains both the target and the stop resolves to `ambiguous`,
claims neither touch time, and is excluded from every economic metric with its
count reported. It is the one place a backtest can flatter itself while both
readings look plausible, and only one of them is profitable.

§41 rule 9 is enforced rather than documented: `economic_report` takes a cost
model as a required argument and refuses without one. [[ADR-048]] records why
that is ADR-009's reasoning kept rather than dropped — a caveat does not travel
with a number, and a required argument does.

## Links

- Requirement: [[REQ-BT-001]]
- Decision: [[ADR-048]], superseding [[ADR-009]] on returns
- Builds on: [[REQ-WP-007]], [[REQ-WP-010]]
- Unblocks: nine of the seventeen [[REQ-EXP-001]]-family experiments
