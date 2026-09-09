---
id: SPEC-040-dex-incremental
requirement: REQ-EXP-007
speckit_path: specs/040-dex-incremental/spec.md
status: draft
---

## Summary

EXP-007's five cumulative arms for ETH, over the machinery extracted from
[[REQ-EXP-004]] rather than copied — two copies of "each arm contains the
previous and adds one family" would drift, and the two experiments' increments
would stop meaning the same thing.

Every DEX family resolves to nothing in today's registry, so four of the five
arms report as not run with their reasons. [[REQ-WP-015]] and [[REQ-WP-016]]
compute divergence, depth asymmetry and swap imbalance; PRD §19 registration for
them is separate work. A test asserts that state, so when the registration
happens it fails and says what to update — the report stops saying "not run" on
purpose rather than by accident.

One prefix had to be narrowed: `basis_` matched the registry's `basis_bps`,
which is PRD §16's perp-spot basis and a CEX derivatives feature. The DEX
divergence arm would have scored it and reported its contribution as the DEX
view's.

## Links

- Requirement: [[REQ-EXP-007]]
- Criteria derived: `docs/superpowers/specs/2026-09-09-experiment-acceptance-design.md`
- Builds on: [[REQ-EXP-004]], [[REQ-WP-015]], [[REQ-WP-016]]
