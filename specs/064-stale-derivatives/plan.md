# Implementation Plan: A stale derivatives state is refused

**Branch**: `wp-026-stale-derivatives` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

`require_fresh(newest_event_ns, *, at_ns, staleness_ns)` in `derivatives/state.py`,
called from the three places that read polled state, plus `StaleState` and a
stated default.

## The finding that changed the plan

The spec's FR-007 said every feature would inherit the rule through the shared
point-in-time path. **There is no shared path.** `state_at` was written as the
package's one seam and its docstring says so — "a rule each call site has to
remember is a rule one call site will forget" — and no feature ever called it.
`grep` for `state_at` outside its own module and `__init__` returns nothing.

Funding filters on `next_funding_time_ns`, open interest builds its own series,
liquidations read events. A staleness rule placed only in `state_at` would have
protected nothing at all, while looking exactly like the criterion being met.

So the rule goes in a free function that each reader calls, and the docstring
records why it cannot be a method on a seam nobody uses.

## Technical Context

**Language/Version**: Python 3.12 · **Dependencies**: none new · **Storage**: none

**Testing**: pytest with `@pytest.mark.trace("REQ-WP-026")`, plus a mutation sweep.

**Constraints**: age from event time; boundary inclusive; the z-score's history untouched.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **II. Time is not one thing** | Age is measured from event time, never ingest. | **Pass**, and stated in the contract. |
| **X. Thresholds are configuration** | The tolerance is a parameter with a stated default. | **Pass.** A default is not a hidden threshold; an absent bound is. |
| **I. No look-ahead** | Untouched — the existing rule still refuses a later state. | **Pass**, asserted unchanged. |

No violations.

## Project Structure

```text
src/channelflow/derivatives/state.py          # StaleState, DEFAULT_STALENESS_NS, require_fresh
src/channelflow/derivatives/funding.py        # settled_funding and its four readers
src/channelflow/derivatives/openinterest.py   # oi_series and its readers
tests/unit/derivatives/test_staleness.py      # NEW
tests/unit/derivatives/conftest.py            # NOT_ABOUT_FRESHNESS
```

**Structure Decision**: a free function rather than a method, because the three
readers find their newest observation differently — the latest state, the last
settled interval, the last open-interest point — and only the age is shared.
