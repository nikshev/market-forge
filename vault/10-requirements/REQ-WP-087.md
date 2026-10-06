---
id: REQ-WP-087
title: "What the extremum detector and the channel fit do across a gap in the bar series"
type: work-package
prd_ref: "§13A, §13.1, §32; the stateful-feature gap rule of §15/§18 acceptance"
prd_lines: "4752-4782, 6750-6758, 6806-6812"
phase: null
status: specified
depends_on: [REQ-WP-086, REQ-WP-006, REQ-WP-019]
tags: [channels, extrema, data-quality, no-look-ahead]
hard_gated: false
---

## Requirement

Both models count **bars**, not time, and neither knows a bar is missing. Read from the code on 2026-10-04:

- the channel fit takes "the most recent `lookback` finalized bars" (`lookback` is 60 by default;
  `channels/window.py`), so over a hole the 60 bars cover as long as the hole makes them;
- the directional-change detector (`extrema/detector.py`) advances one bar at a time and measures confirmation
  in bars (`confirmation_lag_bars`); a jump in price across a hole looks to it like one step.

Measured the same day on ETHUSDT 1h, which has a hole of 148 hourly bars (26.09 06:00 → 02.10 11:00): a LOW
turning at 25.09 22:00 is recorded as known at 02.10 12:00 with `confirmation_lag_bars` of 10, a week later;
and the channel on 02.10 is fitted to a window that, counted in time, reaches back more than a week before
its first bar.

The PRD does not say what a model does when bars are missing. It states the principle for other stateful
engines: "forced sequence gap disables book features" (§15 acceptance) and "forced log gap disables stateful
features until repaired" (§18 acceptance), §32 makes missing bars a health metric with `GOOD` / `DEGRADED` /
`STALE` states, and §13.1 requires that a snapshot never carry hindsight. This requirement is to **decide, and
then test, what the detector and the channel do across a gap**, so that a number built on bars from either side
of a hole is never presented as if it were built on a continuous series.

## Acceptance

**Derived, not quoted**: the PRD has no rule for a gap in the bar series of the channel or the detector, so
each line below is derived from a rule it does state, named beside it. They assume the policy recommended in
the Notes (restart at the gap); the owner's confirmation of that policy is what the note waits on, and it
stays `draft` until then.

- A hole of more than one timeframe step is detected by the model itself, from the bars it is given, not by
  its caller. *(§13.1: the model guards its own invariant; the caller cannot be trusted to filter.)*
- The extremum detector's state (direction, running extreme, open candidate) does not carry across a hole: the
  first bar after it starts a fresh observation, and no confirmation is emitted whose turn is before the hole
  and whose confirming bar is after it. *(§15 and §18 acceptance: "forced gap disables stateful features until
  repaired"; the detector is a stateful engine.)*
- The channel is fitted only to bars after the hole. Until `lookback` contiguous bars exist after it the
  snapshot is absent (or carries a flag saying its window is short), and never reaches over the hole.
  *(§13.1, and the same rule: no state straddles an outage.)*
- A confirmed extremum states its confirmation lag in time as well as in bars. *(§32: missing bars is a health
  metric; a lag in bars is only meaningful on a contiguous series.)*
- None of this reads a bar later than the instant it answers for: a test appends later bars and checks that the
  record at the earlier instant is unchanged. *(Principle I; §35.3's family of tests.)*
- The size of a "hole" is a configuration value with a default of one missing bar, not a constant. *(Principle X.)*
- On a fixture with one hole, and on the live ETHUSDT 1h series (a hole of 148 bars), the records before and
  after the hole come out as two separate runs, and a count of records that straddle it is zero.

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

**The decision this needs from the owner.** Three defensible policies, with a recommendation:

1. **Bridge** (today): treat the bars as consecutive. Simple, and wrong across a long hole; the lag and the
   window then lie.
2. **Restart at the gap** (recommended): a hole of more than one step ends the model's state. The detector
   forgets its direction and running extreme; the channel is fitted only to bars after the hole and is absent
   until `lookback` of them exist (or is flagged short). Nothing is invented and nothing crosses the hole. It is
   the same shape as the OFI rule that the previous observation is not the successor after an outage.
3. **Fill** the hole (carry-forward or interpolate): rejected in advance, since it fabricates bars (§0's
   immutability and the no-hindsight rule).

A threshold for "a hole" is a configuration value (Principle X), not a constant. This note stays in `draft`
until the owner confirms the policy; the acceptance above is derived on the assumption that it is option 2.
