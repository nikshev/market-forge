---
id: REQ-WP-029
title: A replay records the extrema it detected
type: work-package
prd_ref: "§25.1, §29.B, §45 Phase 1A"
prd_lines: "4198-4210, 6724-6737"
phase: 1
status: implemented
depends_on: [REQ-WP-028, REQ-PIPE-001, REQ-INFRA-003, REQ-WP-019]
tags: []
---

## Requirement

[[REQ-WP-028]] put extrema on the canonical plane, behind an endpoint, and on
the chart. Its own outcome note recorded what it did not do:

> Nothing writes extrema yet. The detector produces them and no pipeline stores
> them; the tables and the endpoint are reachable and empty.

That is the sixth time this session a mechanism has been built with nothing
calling it, and each previous one was closed by writing the caller down as a
requirement rather than by building a seventh mechanism. This is that caller.

[[REQ-PIPE-001]]'s replay already turns bars into channel snapshots and signals
on the plane. The detector takes the same bars and produces candidates and
confirmations. One replay should write all four, from one pass of the same
input, so that what the chart reads was produced by the same run that produced
everything else it reads.

**Through the bus, not beside it.** [[REQ-INFRA-003]] built an event bus whose
own outcome note admits its weakness: "one caller, one capability, proven by
tests rather than by use". A second producer and a second pair of consumers is
what turns that from an abstraction into a seam.

## Acceptance

- a replay detects extrema over the bars it was given and records both
  candidates and confirmations;
- the detector's output is published as events and the recorders subscribe,
  rather than being handed to a writer directly;
- a caller's own subscriber sees the same events, without editing the pipeline;
- a second replay over input already recorded writes nothing and says how much
  it skipped;
- what a replay already records — bars, snapshots, signals, dataset identity —
  is unchanged;
- an extremum confirmed on a bar is published on that bar, not at the end: a
  live process attaching the same subscribers must see the same order.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-067-record-extrema]]
- **Tests:**
    - `tests/unit/pipeline/test_record_extrema.py::test_a_caller_sees_every_extremum_event`
    - `tests/unit/pipeline/test_record_extrema.py::test_a_confirmation_arrives_in_its_own_bar_s_turn`
    - `tests/unit/pipeline/test_record_extrema.py::test_a_longer_replay_adds_only_what_is_new`
    - `tests/unit/pipeline/test_record_extrema.py::test_a_replay_fills_the_extremum_tables`
    - `tests/unit/pipeline/test_record_extrema.py::test_a_second_replay_writes_no_extrema`
    - `tests/unit/pipeline/test_record_extrema.py::test_a_series_with_no_turn_records_nothing_and_refuses_nothing`
    - `tests/unit/pipeline/test_record_extrema.py::test_an_observer_does_not_change_what_is_recorded`
    - `tests/unit/pipeline/test_record_extrema.py::test_what_the_replay_already_recorded_is_unchanged`
    - `tests/unit/pipeline/test_record_extrema.py::test_what_was_written_is_what_the_detector_produced`
- **Code:**
    - `src/channelflow/events.py`
    - `src/channelflow/pipeline/replay.py`
- **Outcomes:** [[OUT-2026-09-10-implement-record-extrema]], [[OUT-2026-09-10-plan-record-extrema]], [[OUT-2026-09-10-requirement-record-extrema]], [[OUT-2026-09-10-spec-record-extrema]]
<!-- trace:end -->

## Notes

**Detection runs over the same bars the replay was given, in its own pass.**
The backtest runner owns its loop and offers no per-bar hook; adding one to feed
a detector would change a component that has nothing to do with extrema. Two
passes over one list is deterministic and cheap, and Principle VII is satisfied
by the *events* being identical, not by the iteration being shared.

**Nothing here changes the detector.** Where a turn is confirmed, and under
which threshold, is [[REQ-WP-019]]'s and stays there.
