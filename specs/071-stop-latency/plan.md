# Implementation Plan: A stop update is not effective until it is acknowledged

**Branch**: `wp-033-stop-latency` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

One value object, `ActivationLatency`, and one distinction inside the replay:
the stop the policy has **decided** is not the stop the exchange is **obeying**.

Today those are one variable. Splitting them is the whole change: triggers are
evaluated against the active stop, the policy is shown the decided one — because
that is what a live engine knows about its own outstanding request — and a
decision becomes active only after its acknowledgement instant.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: PRD §44A.27's own example, replayed literally, plus a mutation
sweep. The existing 20 replay tests are the regression floor.

**Constraints**: zero latency must reproduce the prior outcomes field for field.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **I. No look-ahead, ever** | A stop effective before it was acknowledged is protection borrowed from the future. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-033`, markers on every test. | **Pass.** |
| **PRD §41 rule 9 (costs)** | Latency joins fees and slippage as a modelled cost of being real. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/stops/replay.py       # + ActivationLatency, decided vs active
src/channelflow/stops/__init__.py     # + the export
tests/unit/stops/test_latency.py      # NEW
```

## The property that makes this safe to land

Existing paths are spaced a minute apart and the default latency is 160 ms, so
every decision is active by the next point and **no existing outcome moves**.
That is a claim to verify, not to assume: the 20 existing replay tests run
unchanged under the new default, and if any of them moves, the default is
reaching further than the PRD's example says it should.

The new tests therefore work at sub-second spacing, where the gap is expressible
— which is where the PRD's example lives.

## Counting, and what a count means

`stop_updates` keeps its meaning: decisions the policy made. A second field,
`stop_updates_activated`, counts the ones the exchange obeyed inside the path.
Collapsing them would make the spec's own edge case unobservable — a latency
longer than the path leaves a position running on its initial stop while the
report says the stop was updated four times.
