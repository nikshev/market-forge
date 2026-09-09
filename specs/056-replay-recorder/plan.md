# Implementation Plan: A replay writes to the canonical plane

**Branch**: `pipe-001-replay-recorder` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

Two observers on the backtest runner, two recorders that buffer what they see,
and two entry points — trades to bars, bars to snapshots and signals — whose
result names the dataset it produced.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: `channelflow.backtest`, `channelflow.tables`,
`channelflow.experiments`.

**Testing**: 12 unit tests, including the end-to-end loop through the durable
repository.

**Target Platform**: `src/channelflow/pipeline/`, with two optional hooks added
to `backtest/runner.py`.

**Constraints**: FR-004 (one row per signal), FR-006 (observers cannot steer),
FR-010 (two replays, one identity).

**Scale/Scope**: 1 package, 1 module, 12 tests, 10 mutations.

## Constitution Check

- **V (finalized records are not rewritten)** — only finalized bars are written,
  and the plane's history is immutable beneath them.
- **VII (live and replay are the same code)** — the sinks attach to the hooks
  the producing subsystems already offer, so a live feed has no second path.
- **XI (results are reproducible)** — two replays of one series produce one
  dataset identity, which is the property that makes the identity worth citing.
- **XIV** — traces to REQ-PIPE-001.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/pipeline/replay.py    # NEW: recorders and entry points
src/channelflow/backtest/runner.py    # + two optional observers
```

**Structure Decision**: the runner gained observers rather than a return value.
Its report is a summary and changing that would break every caller; the
snapshots and candidates are what a recorder needs, and refitting them outside
the loop would be a second fitting path that could disagree with the first.

## Approach

**A signal is written once, in its final state.** `SignalMachine.on_bar`
returns the live candidate on every bar it is alive for, each time a more
complete version of the same frozen object. A recorder that wrote each would put
a row per bar in the table, every one a partial history of one signal, and a
reader counting signals would count bars.

**Observers observe.** Neither is consulted and the report is identical with or
without them, which a test asserts by comparing a recorded run against a plain
one. A recorder that could steer would make a recorded run a different run.

**The caller's runner is copied.** One that came back carrying sinks would write
again on its next use, into whatever store the first run happened to use.

**The recording names only what it filled.** A dataset naming a table nobody
wrote to would claim the run read it — and a replay writes to some of these and
not others depending on what the series produced.

## Complexity Tracking

> No violations.
