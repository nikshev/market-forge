---
id: OUT-2026-09-10-implement-record-extrema
step: implement
records: [REQ-WP-029]
commit: null
---

## What was done

`ExtremumObserved` and `ExtremumConfirmed` on the bus, an `ExtremumRecorder`
subscribing to both, and a detector pass inside `record_replay`.

9 new tests, 1635 in the suite, mypy clean at 169 files, 10 of 10 mutants
caught.

**The extremum tables are no longer reachable and empty.** A replay now writes
bars, channel snapshots, signals, confirmed extrema and candidates from one pass
of one input — so what the chart reads about turns was produced by the same run
as everything else it reads.

## What the mutation sweep found

Two survivors, both weak assertions of mine rather than weak code:

- **The ordering test asked whether the sequence was sorted.** A batch flushed
  at the end publishes every confirmation and then every candidate — a sequence
  that is *also* unsorted, so the check passed for exactly the implementation it
  was written to reject. It counts alternations now.
- **The skip test used `>=`.** `Recording.skipped` is the whole run's tally, so
  the channel snapshots alone satisfied the bound and dropping the confirmations
  from the count went unnoticed. Both skip tests now enumerate every term.

## What is still open

- **A neighbouring test had to change**, and it is worth saying why rather than
  burying it: `test_a_second_replay_over_the_same_bars_writes_nothing` summed two
  terms because two recorders existed when it was written. It sums four now. A
  term forgotten there would make a run that skipped less than it should look
  correct, which is why both are enumerated rather than bounded.
- **Nothing attaches these subscribers live.** PRD §25.1's live mode still does
  not exist; the events are published by a replay and consumed by one recorder
  and whatever a caller subscribes.
- **The detector still accumulates rather than emitting.** Publishing per bar
  works by watching its list grow. Changing that is [[REQ-WP-019]]'s call.
