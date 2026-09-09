---
id: OUT-2026-09-09-implement-order-flow-exhaustion
step: implement
records: [REQ-EXP-014]
commit: null
---

## What was done

`channelflow.research.exhaustion`: EXP-014's conditional study and its
point-in-time repeat, over the six bullets the PRD names. 17 tests, fifteen
mutations, all caught.

## A threshold that is also a look-ahead

The predictive arm reads only trailing windows, which is the obvious half of
Principle I here. The other half is the number it compares those windows
against. A quantile taken over the whole series has read every bar the forecast
is about, and nothing in the output says so — the calls look reasonable, the
precision looks like skill, and the arm passes every test about windows.

`trailing_calls` is public for exactly that reason: it makes the property
testable. The calls made over a prefix must be the calls the whole series makes
at those same bars.

## Three survivors, and two of them were one fixture

Two of the three were the same blindness twice. A fixture whose two halves look
alike cannot tell a trailing quantile from a whole-series one, because both land
on the same number — so the look-ahead mutation changed nothing. The test now
runs on a series whose second half sits a hundred times higher than its first.

The third was the horizon's own last bar. Dropping it costs the study the calls
furthest ahead of each turn, which are the ones a forecast is worth anything
for, and the precision that remains still reads as a plausible number. A signal
that spikes exactly once, `horizon` bars before each turn, pins the boundary
from both sides: five calls and five hits at `horizon`, five calls and none at
`horizon + 1`.

## Two things the fixtures changed about the code

**A call is strictly above the trailing quantile, not at or above it.** Order-flow
signals are zero on most bars; the quantile of such a series is zero; "at or
above zero" calls every single bar. That produces a precision exactly equal to
the base rate and a lift of exactly one — indistinguishable from "this signal
carries nothing", for a reason that has nothing to do with the signal.

**The forecast rule has a floor rather than a comparison against one.** Two
control series built to carry no information — waves on periods no turn follows
— scored lifts of 1.07 and 1.16 over forty calls. `lift > 1.0` called both of
them forecasts. The floor is a required argument now and has to sit above one.

## Mutation results

Fifteen mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| A bullet is dropped | `test_every_bullet_the_prd_names_is_studied` |
| The conditional window is one-sided | `test_a_signal_that_explains_but_does_not_forecast_is_named_as_such` |
| The conditional arm does not declare itself retrospective | `test_the_conditional_arm_declares_itself_retrospective` |
| The calling threshold is taken over the whole series | `test_the_calling_threshold_reads_no_bar_at_or_after_the_decision` |
| Bars without a full horizon are decided too | `test_the_predictive_arm_decides_only_bars_with_a_full_horizon_ahead` |
| A call is at or above the quantile | `test_the_two_arms_disagree_on_the_same_series` |
| The control gap is ignored | `test_control_bars_are_kept_away_from_every_turn` |
| The lift floor is a comparison against one | `test_a_signal_related_to_nothing_is_named_as_such` |
| The effect floor is ignored | `test_a_signal_related_to_nothing_is_named_as_such` |
| A missing series is defaulted to zeros | `test_a_missing_signal_is_refused` |
| An extremum outside the series is accepted | `test_an_extremum_outside_the_series_is_refused` |
| The note loses the separation | `test_the_conditional_arm_declares_itself_retrospective` |
| Precision over no calls is zero | `test_a_signal_that_never_stands_out_has_no_precision` |
| The horizon is one bar short | `test_the_horizon_includes_its_own_last_bar` |
| The horizon reaches backwards | `test_the_horizon_includes_its_own_last_bar` |

## What is still open

- **No signal is selected.** The fixtures are analytic by construction and
  establish that the study can conclude each of its four readings, not what it
  concludes on real books.
- **Six research judgements move every number here**: the window around a turn,
  the forecast horizon, the control gap, the calling quantile, the effect floor
  and the lift floor. All six are required arguments and none is validated.
- **The effect size is a difference of means over a pooled spread.** It says a
  signal is different around turns, not that the difference is the same shape at
  every turn.
