---
id: OUT-2026-09-08-spec-channel-baseline
step: spec
records: [REQ-WP-006]
commit: null
---

## What was done

Specified REQ-WP-006 as `specs/007-channel-baseline/spec.md`: 16 functional
requirements, 8 success criteria.

## What was decided

- **The hard invariant is enforced in the model, not documented for callers.**
  PRD §13.1 states `source_max_event_time <= as_of` and §2.1 identifies
  repainting as the critical risk the product exists to avoid. FR-007 and FR-008
  make the model refuse rather than trust; SC-001 tests it the only way that
  proves anything — refit at an unchanged `as_of` after appending later bars and
  demand an identical snapshot.
- **Two definitions the PRD names but never gives**, both settled in [[ADR-007]]:
  `slope_normalized` is the slope over the residual standard deviation, and
  `channel_quality` uses the six of nine submetrics whose inputs exist. This is
  the third requirement running where the PRD specifies a field name without its
  meaning.
- **An unavailable submetric is omitted, never defaulted** (FR-014). Defaulting
  to a neutral value would move the score toward the middle for reasons no
  reader could see, and would make a six-part score silently comparable with a
  later nine-part one.
- **Only finalized bars, enforced here** (FR-009). PRD §12 says signals use
  finalized bars by default; putting the filter in the model means a caller
  cannot forget it.
- **Forecast horizons are left empty rather than fabricated.** PRD §13.1's
  snapshot carries them and §13.7 defines them, but this is Baseline A. An empty
  list is honest; a plausible-looking one would not be.

## What is still open

- **The quality weights are a starting point, not a finding.** PRD §48 lists
  research questions that must be answered before any of this drives a decision,
  and §13.9 says ML scoring replaces the transparent average later.
- **Three submetrics are unavailable**: forecast calibration needs §13.8's
  forecast channel, regime compatibility needs §20's engine, and age needs
  channel-lifetime tracking that nothing yet keeps.
- **Baselines B through E are separate models** behind the same interface.
- **No persistence.** PRD §29.6's table is a later concern; immutability here
  honours §0.5 without a storage layer.
