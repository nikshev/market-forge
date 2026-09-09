---
id: REQ-PIPE-001
title: A replay writes what it produced to the canonical plane
type: work-package
prd_ref: "§25.1 Two modes, §29.B canonical tables, §0 item 13"
prd_lines: "4198-4210, 4579-4602, 27"
phase: null
status: implemented
depends_on: ["REQ-STORE-002", "REQ-TBL-001", "REQ-WP-010", "REQ-REPRO-001"]
tags: []
hard_gated: false
---

## Requirement

PRD §25.1 defines two backtest modes, live and replay. PRD §29.B lists the
canonical tables. PRD §0 item 13 requires a research result to be reproducible
from a versioned dataset.

Three requirements built the plane and its tables and left the same question
open in three places, in their own words:

- [[REQ-STORE-001]]: "Nothing writes to this plane."
- [[REQ-TBL-001]]: "Nothing runs a pipeline into this table."
- [[REQ-STORE-002]]: "Nothing fills these tables from a live feed."

Everything downstream waits on it. The durable repository has nothing to serve,
and [[REQ-REPRO-001]]'s dataset reference has nothing to reference — which is
why [[REQ-BIAS-011]] stopped at `specified`.

## Acceptance

- trades aggregated into bars are written, and only the windows the builder
  finalized;
- a window still open when the input ends is not written;
- a replay writes the channel snapshots it fitted, one per bar that had a
  channel;
- a signal is written once, in its final state, rather than once per bar it was
  alive for;
- a replay does not write the bars it read;
- the observers do not change what the run reports;
- a runner passed in comes back without sinks attached;
- the result names only the tables the replay actually wrote to, and a replay
  that produced nothing names nothing;
- two replays of one series produce the same dataset identity;
- the durable repository serves what a replay recorded, with nothing in memory
  between them.

## Scope

**In:** the recorders, their attachment to the producing subsystems' own hooks,
the two entry points, and the dataset identity of what was written.

**Out, and named rather than silently dropped:**

- **A live process.** PRD §25.1's other mode. The sinks here are the ones the
  producing subsystems already offer, so a live feed has no second path to take;
  starting and supervising a process that attaches them is deployment work.
- **Feature snapshots and scores.** The replay produces neither: features come
  from the registry against a book this replay does not have, and a score needs
  them. Their tables exist ([[REQ-STORE-002]]) and stay empty.
- **Incremental or resumable backfill.** One replay, one batch per table. A
  backfill that resumes needs to know what it already wrote, which is a
  watermark this does not keep.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-056-replay-recorder]]
- **Tests:**
    - `tests/unit/pipeline/test_replay.py::test_a_recording_is_a_value_and_carries_its_counts`
    - `tests/unit/pipeline/test_replay.py::test_a_replay_does_not_rewrite_its_own_input`
    - `tests/unit/pipeline/test_replay.py::test_a_replay_that_produced_nothing_names_nothing`
    - `tests/unit/pipeline/test_replay.py::test_a_replay_writes_the_snapshots_it_fitted`
    - `tests/unit/pipeline/test_replay.py::test_a_signal_is_written_once_in_its_final_state`
    - `tests/unit/pipeline/test_replay.py::test_a_window_still_open_at_the_end_is_not_written`
    - `tests/unit/pipeline/test_replay.py::test_the_api_serves_what_a_replay_recorded`
    - `tests/unit/pipeline/test_replay.py::test_the_caller_s_runner_comes_back_without_sinks`
    - `tests/unit/pipeline/test_replay.py::test_the_observers_do_not_change_what_the_run_reports`
    - `tests/unit/pipeline/test_replay.py::test_the_recording_names_only_the_tables_it_wrote`
    - `tests/unit/pipeline/test_replay.py::test_trades_become_bars_in_the_table`
    - `tests/unit/pipeline/test_replay.py::test_two_replays_of_one_series_write_the_same_dataset`
- **Code:**
    - `src/channelflow/pipeline/__init__.py`
    - `src/channelflow/pipeline/replay.py`
- **Outcomes:** [[OUT-2026-09-09-implement-replay-recorder]], [[OUT-2026-09-09-plan-replay-recorder]], [[OUT-2026-09-09-requirement-replay-recorder]], [[OUT-2026-09-09-spec-replay-recorder]]
<!-- trace:end -->

## Notes

Hand-written: PRD §46 has no work package for wiring §25's replay to §29's
tables. This section is human territory and is never machine-rewritten.
