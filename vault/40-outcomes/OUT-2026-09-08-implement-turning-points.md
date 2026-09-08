---
id: OUT-2026-09-08-implement-turning-points
step: implement
records: [REQ-WP-019, REQ-NRT-A, REQ-NRT-B, REQ-NRT-C, REQ-NRT-D, REQ-NRT-E]
commit: null
---

## What was done

`channelflow.extrema`: PRD §13A.5's directional-change baseline with §13A.1's
two timestamps, §13A.5's five threshold modes, §13A.6's prominence filter,
[[ADR-022]]'s causality guard, and §13A.28's Tests A to E. 37 tests.

Five `hard_gated` requirements move off `draft` for the first time since
extraction: REQ-NRT-A, B, C, D and E now each have between two and five
verifying tests.

## Two real bugs the tests caught

- **The detector assumed a direction instead of observing one.** It started in
  `UP` and, on a falling series, confirmed a HIGH from the very first bar — an
  extremum from a swing whose formation was never seen. Its own comment said
  not to do that. It now tracks both extremes until price moves a full
  threshold from one of them; that move settles the direction, and the extreme
  it moved away from is discarded rather than emitted.
- **`zip(recent, recent[1:], strict=True)`** cannot have equal lengths, so
  every ATR and realized-volatility computation raised. Paired as
  `recent[:-1]` with `recent[1:]` instead, which keeps `strict=True` meaning
  something.

## And one bug in a test

`test_a_threshold_uses_only_bars_at_or_before_the_instant` appended a "later"
series built from index zero, so the two series carried identical timestamps
and the filter had nothing to exclude. The test passed while checking nothing.
The helper now takes a start index and the fixture says why.

## What was decided

- **`ConfirmedExtremum` refuses `known_at < extremum_time` at construction.**
  Test C then checks a property the type enforces. PRD §13A.1's whole point is
  that "any backtest that acts on the 10:00 label before 10:30 is invalid" —
  and a record claiming otherwise is that invalid backtest, expressed as data.
- **The threshold in force is stored on the confirmation.** Recomputing it
  later, for a report or a chart, is exactly how a point-in-time value silently
  becomes a hindsight one.
- **Test A appends random bars, over three seeds, and compares every field.**
  A fixed continuation could be the one series a broken detector survives; a
  count comparison would pass a detector that rewrote every field; and the
  first assertion is that the outputs are non-empty, because comparing two
  empty lists passes.
- **Test A is checked from both directions.** Appending must not change
  anything, and truncating must not add anything — the prefix test runs the
  detector over every prefix length and asserts the confirmations only ever
  grow by appending.
- **REQ-WP-019 stops at `tested`** ([[ADR-023]]). Two of its five acceptance
  criteria need REQ-WP-017 and REQ-WP-018.

## Mutation results

Six mutations, all caught, each restore verified by comparing the file against
its backup:

| Mutation | Caught by |
| --- | --- |
| `known_at` backdated to the extremum | `test_the_confirmation_lag_is_the_distance_between_them` (+2) |
| The model stops refusing `known_at < extremum_time` | `test_a_record_claiming_to_be_known_before_it_happened_cannot_be_built` |
| The threshold reads the whole series, not up to `t` | `test_a_threshold_uses_only_bars_at_or_before_the_instant` |
| The prominence filter is dropped | `test_a_swing_below_the_minimum_prominence_is_not_confirmed` |
| A centered transform is let through | `test_d_a_centered_transform_is_refused_by_the_production_path` |
| The direction is assumed rather than observed | `test_a_high_is_dated_to_its_peak_and_known_at_the_crossing` (+1) |

The restore verification is new, after REQ-WP-009's silent `git checkout` on an
untracked file. The harness now compares each restored file against its backup
and says so.

## What is still open

- **REQ-NRT-F stays at `draft`**: it tests GMDH derivative root stability and
  there is no GMDH.
- **§13A.30's steps 3 to 5** — causal local-polynomial slope, Kalman filtered
  slope, channel-conditioned extremum classes — are named in REQ-WP-019's
  ordering and not built.
- **`TurningPointForecast` is not implemented**: a model output with no model.
- **Prominence uses no ATR.** `prominence_atr` is always `None` on emitted
  records, because the detector does not yet compute an ATR alongside the
  threshold. §13A.6's example criterion is expressible and untested against
  real data.
- **The extrema are not wired into anything**: no chart overlay (§13A.25), no
  alert semantics (§13A.24), no storage (§13A.21).
