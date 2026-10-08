---
id: REQ-WP-087
title: "What the extremum detector and the channel fit do across a gap in the bar series"
type: work-package
prd_ref: "§13A, §13.1, §32; the stateful-feature gap rule of §15/§18 acceptance"
prd_lines: "4752-4782, 6750-6758, 6806-6812"
phase: null
status: implemented
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
- **Specs:** [[SPEC-141-detector-gap-policy]]
- **Tests:**
    - `tests/channels/test_channel_gap.py::test_a_series_with_a_hole_replays_to_the_end_with_the_default_runner`
    - `tests/channels/test_channel_gap.py::test_a_window_of_one_bar_after_a_hole_is_refused_not_crashed`
    - `tests/channels/test_channel_gap.py::test_channel_no_look_ahead`
    - `tests/channels/test_channel_gap.py::test_channel_window_absent_when_no_bars_after_gap`
    - `tests/channels/test_channel_gap.py::test_channel_window_short_after_gap`
    - `tests/channels/test_channel_gap.py::test_channel_window_starts_after_gap`
    - `tests/channels/test_channel_gap.py::test_fit_window_enforces_the_floor_only_after_a_hole`
    - `tests/channels/test_channel_gap.py::test_the_channel_returns_at_the_configured_minimum_and_says_it_is_short`
    - `tests/channels/test_channel_gap.py::test_the_minimum_must_be_a_line_and_no_more_than_the_lookback`
    - `tests/extrema/test_detector_gap.py::test_confirmation_lag_only_from_bars_after_hole`
    - `tests/extrema/test_detector_gap.py::test_contiguous_bars_normal_tracking`
    - `tests/extrema/test_detector_gap.py::test_no_look_ahead_appending_later_bars`
    - `tests/extrema/test_detector_gap.py::test_one_missing_bar_bridges_at_default_threshold`
    - `tests/extrema/test_detector_gap.py::test_threshold_default_one_bridges_one_missing`
    - `tests/extrema/test_detector_gap.py::test_threshold_two_keeps_two_missing_and_restarts_on_three`
    - `tests/extrema/test_detector_gap.py::test_threshold_zero_any_gap_restarts`
    - `tests/extrema/test_detector_gap.py::test_turn_before_hole_confirm_after_gives_no_confirmation`
    - `tests/extrema/test_detector_gap.py::test_two_missing_bars_resets_state`
    - `tests/unit/channels/test_gap_fields.py::test_the_snapshot_states_how_many_bars_its_window_held`
    - `tests/unit/channels/test_gap_fields.py::test_window_short_says_whether_the_window_is_shorter_than_the_lookback`
    - `tests/unit/extrema/test_gap_fields.py::test_a_confirmed_extremum_states_its_confirmation_lag_in_time`
    - `tests/unit/extrema/test_gap_fields.py::test_confirmation_lag_ns_defaults_to_zero_when_a_producer_has_not_computed_it`
    - `tests/unit/extrema/test_is_gap.py::test_a_corrected_bar_reissued_on_the_previous_timestamps_is_not_a_gap`
    - `tests/unit/extrema/test_is_gap.py::test_a_distance_that_is_not_whole_steps_is_rounded_not_floored`
    - `tests/unit/extrema/test_is_gap.py::test_a_non_positive_timeframe_is_refused_naming_the_variable[-60000000000]`
    - `tests/unit/extrema/test_is_gap.py::test_a_non_positive_timeframe_is_refused_naming_the_variable[0]`
    - `tests/unit/extrema/test_is_gap.py::test_contiguous_bars_are_not_a_gap`
    - `tests/unit/extrema/test_is_gap.py::test_one_missing_bar_bridges_at_the_default_threshold`
    - `tests/unit/extrema/test_is_gap.py::test_threshold_two_keeps_two_missing_bars_and_restarts_on_three`
    - `tests/unit/extrema/test_is_gap.py::test_threshold_zero_restarts_on_any_missing_bar`
    - `tests/unit/extrema/test_is_gap.py::test_two_missing_bars_are_a_gap_at_the_default_threshold`
    - `tests/unit/test_settings_gap.py::test_a_blank_threshold_is_the_default_not_a_parse_failure`
    - `tests/unit/test_settings_gap.py::test_a_deployment_that_sets_nothing_gets_one_missing_bar`
    - `tests/unit/test_settings_gap.py::test_a_negative_threshold_is_refused_naming_the_variable[-148]`
    - `tests/unit/test_settings_gap.py::test_a_negative_threshold_is_refused_naming_the_variable[-1]`
    - `tests/unit/test_settings_gap.py::test_something_that_is_not_a_whole_number_is_refused[1.5]`
    - `tests/unit/test_settings_gap.py::test_something_that_is_not_a_whole_number_is_refused[1_0]`
    - `tests/unit/test_settings_gap.py::test_something_that_is_not_a_whole_number_is_refused[abc]`
    - `tests/unit/test_settings_gap.py::test_something_that_is_not_a_whole_number_is_refused[two]`
    - `tests/unit/test_settings_gap.py::test_the_threshold_is_a_whole_number_of_missing_bars[0-0]`
    - `tests/unit/test_settings_gap.py::test_the_threshold_is_a_whole_number_of_missing_bars[1-1]`
    - `tests/unit/test_settings_gap.py::test_the_threshold_is_a_whole_number_of_missing_bars[3-3]`
    - `tests/unit/test_settings_gap.py::test_zero_is_a_threshold_not_a_mistake`
- **Code:**
    - `src/channelflow/bars/gaps.py`
    - `src/channelflow/channels/huber.py`
    - `src/channelflow/channels/kalman.py`
    - `src/channelflow/channels/models.py`
    - `src/channelflow/channels/quantile.py`
    - `src/channelflow/channels/rolling_ols.py`
    - `src/channelflow/channels/window.py`
    - `src/channelflow/extrema/detector.py`
    - `src/channelflow/extrema/models.py`
    - `src/channelflow/settings.py`
    - `src/channelflow/tables/channels.py`
- **Outcomes:** [[OUT-2026-10-06-spec-detector-gap-policy]], [[OUT-2026-10-06-tasks-detector-gap-policy]], [[OUT-2026-10-07-implement-gap-policy]], [[OUT-2026-10-08-implement-gap-window-floor]]
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
