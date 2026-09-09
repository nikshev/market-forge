# Implementation Plan: Adaptive stop-management policy comparison

**Branch**: `exp-017-stop-policies` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

One research module replaying EXP-017's seven policies and seven ablations over
one set of entries through [[REQ-WP-020]]'s own loop, plus the instrumentation
that loop needed to report the walk ([[ADR-052]]).

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.stops`.

**Testing**: pytest, over a path with two shakeouts — each vetoed by a different
capability, so the arms form a ladder — and a clean trend where the engine's
machinery has nothing to save.

**Target Platform**: `src/channelflow/research/`, with additions to
`stops/models.py` and `stops/replay.py`.

**Constraints**: FR-001 and FR-002 (the same entries), FR-012 (an ablation is a
change to what the policy sees), FR-013 (the verdict).

**Scale/Scope**: 1 module, 1 replay extension, 19 + 5 tests.

## Constitution Check

- **I (no look-ahead, ever)** — the anchors carry `known_at_ns` and the policy
  already refuses a future-confirmed swing; nothing here relaxes that.
- **IV (a number without its baselines is not a result)** — the engine is scored
  against six simpler policies on the same entries.
- **VII (live and replay are the same code)** — every arm runs through
  `Replay` and `StopPolicy`. The ablations change the path, not the policy.
- **X (thresholds are configuration)** — the capabilities are a frozen record,
  and the improvement floor is a required argument.
- **XIV** — traces to REQ-EXP-017.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/research/stop_policies.py   # NEW
src/channelflow/stops/models.py             # + the walk on StopPolicyOutcome
src/channelflow/stops/replay.py             # records it; passes data_quality_ok
```

**Structure Decision**: an ablation is a transformation of the path, not a branch
inside the policy. A capability the engine does not have cannot veto and cannot
supply a level, so removing it is exactly removing what it contributed — and a
branch inside the policy would be a second policy that only looked like the
first.

## Approach

**Four of the twelve metrics are properties of the walk**, not of the exit, and
the replay is the only place that holds the path and the position's side
together. Computing an excursion elsewhere means re-deriving the side
convention, and a sign error there swaps the favourable and adverse excursions
while both stay plausible. [[ADR-052]].

**The premature-stop rate is a property, not a field.** §44A.29's warning —
"an infinitely wide stop would make it look good while destroying risk control"
— only stops being advice when the number cannot be lifted out on its own.

**A path that never stopped is marked out** at its last price, charged fees and
not a stop's adverse slippage. A policy that never exits has no losses and would
win every comparison; charging it for a fill it never took would be the opposite
error.

**The burden is on the engine.** It has to beat the best of the six by the floor
on the same entries after costs, and the best of the six explicitly excludes
itself — counting the engine among its own rivals makes it the best of them by
construction and the margin zero.

## Complexity Tracking

> No violations.
