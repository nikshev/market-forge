# Implementation Plan: A feed going quiet is announced

**Branch**: `wp-035-outage-alerts` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

Two pieces. `channelflow/health.py` turns readings into one of PRD §32's four
states, and `alerting/outages.py` announces the changes.

The assessment is where the requirement lives: **an absent reading is not a
reading within its limit**, and an assessment with nothing to go on is not GOOD.
Every other part is bookkeeping over that.

## Technical Context

**Language**: Python 3.12 · **Dependencies**: none new

**Testing**: the existing alerting suite is the regression floor; new tests for
the assessment, the transitions and the message. Mutation sweep over both files.

**Constraints**: thresholds are arguments ([[PRD §13.11]]); the dispatcher is
[[REQ-WP-034]]'s `Notification` protocol, unchanged.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VII. Live and replay are the same code** | No clock: every instant is an argument, and a duration is a difference between two of them. | **Pass.** |
| **X. Parameters are arguments** | §32 lists nine metrics and no values. | **Pass.** |
| **XIV. Everything is traceable** | `# @trace: REQ-WP-035`, markers on every test. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/health.py                 # NEW: the four states and the assessment
src/channelflow/alerting/outages.py       # NEW: the alert, its renderer, the watch
src/channelflow/alerting/__init__.py      # + the exports
tests/unit/health/test_assessment.py      # NEW
tests/unit/alerting/test_outages.py       # NEW
```

**Structure Decision**: the state model is not inside `alerting`. §32's states
are consumed by signal eligibility, which is not an alerting concern; putting
them under the notifier would make every future consumer import the alerting
package to ask whether a feed is trustworthy.

## The ordering that makes the states usable

The four states are ranked — GOOD, DEGRADED, STALE, INVALID — so "the worst one
decides" is a comparison rather than a chain of conditionals that a tenth metric
would have to be threaded through. The ranking is a property of the enum and is
tested as one, because a mis-ordered rank would make a stale feed outrank an
invalid one and the assessment would still return a plausible state.
