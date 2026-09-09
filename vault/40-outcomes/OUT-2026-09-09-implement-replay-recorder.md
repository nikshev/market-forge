---
id: OUT-2026-09-09-implement-replay-recorder
step: implement
records: [REQ-PIPE-001]
commit: null
---

## What was done

`channelflow.pipeline`: two recorders, two entry points, and two optional
observers added to `BacktestRunner`. 12 tests, 10 mutations, all caught.

The canonical plane now has something in it, and the loop three requirements
left open at both ends is closed: trades in, a replay over the bars they made,
the durable repository answering from what it wrote, and a dataset identity to
cite for any of it.

## The recorder that would have counted bars

`SignalMachine.on_bar` returns the live candidate on every bar it is alive for.
Each call carries a more complete version of the same frozen object — one more
transition than the last.

The obvious recorder writes what it is given, and produces a row per bar. Every
one of those rows is well-formed; every one carries a real prefix of a real
history; and a reader counting signals counts bars. The recorder keeps the
latest per `opened_at_ns` and writes at the end, which is sound because a
candidate cannot reopen on the bar that closed one.

The test for it was weak on the first pass and the sweep said so. "Every stored
signal has at least one transition" passes when the recorder keeps the *first*
state of each candidate rather than the last — one transition per signal, and a
recorder that looks like it works. The stored histories now have to sum to the
report's own transition count.

## A guard nothing could reach

`_recording` skipped a table with no snapshot, and the caller had already
filtered those out before passing them. Two places decided the same thing and
only one of them could ever be wrong, so a mutation removing the guard changed
nothing.

The caller passes every table the replay could have touched now — the bars table
it reads from and never writes included — and the guard decides against the
store. A counter and a table can disagree; the table is the one a reader opens.

## What was decided

- **The observers observe.** Neither is consulted and the report is identical
  with or without them, asserted by comparing a recorded run against a plain
  one. A recorder that could steer would make a recorded run a different run
  from the one it claims to record.
- **A replay does not write the bars it read.** They are its input, and writing
  them would duplicate a series for a replay over a table's own contents.
- **A window still open when the input ends is not written.** It is not a bar
  yet; the builder's watermark decides, and forcing it closed would publish a
  window that may still receive trades.
- **Two replays of one series share a dataset identity.** Principle XI at the
  end of the pipeline, and the property that makes the identity worth citing.

## Mutation results

Ten mutations, all caught, every restore verified:

| Mutation | Caught by |
| --- | --- |
| Every candidate state is written | `test_a_signal_is_written_once_in_its_final_state` |
| Only the first state of a candidate is kept | `test_a_signal_is_written_once_in_its_final_state` |
| The replay writes its own input back | `test_a_replay_does_not_rewrite_its_own_input` |
| The caller's runner is mutated | `test_the_caller_s_runner_comes_back_without_sinks` |
| A table with no snapshot is referenced anyway | `test_the_recording_names_only_the_tables_it_wrote` |
| The snapshot recorder drops what it is given | `test_a_replay_writes_the_snapshots_it_fitted` |
| The observer steers the run | `test_the_observers_do_not_change_what_the_run_reports` |
| The candidate observer never fires | `test_a_signal_is_written_once_in_its_final_state` |
| The bar sink is never flushed | `test_trades_become_bars_in_the_table` |
| An unfinalized window is forced closed | `test_a_window_still_open_at_the_end_is_not_written` |

## What is still open

- **Still no live process.** The sinks are the producing subsystems' own hooks,
  so there is no second path for a live feed — but nothing starts one, and
  supervising one is deployment work.
- **Feature snapshots and scores are still empty tables.** A replay produces
  neither: features come from the registry against a book a bar replay does not
  have, and a score needs them.
- **No resumable backfill.** One replay is one batch per table. Resuming needs a
  watermark saying what was already written, and nothing keeps one — a second
  replay over overlapping input would write the overlap twice.
- **[[REQ-BIAS-011]] is still `specified`.** There is a dataset to cite now, and
  no research module cites one yet. That adoption is the next thing this
  unblocks.
