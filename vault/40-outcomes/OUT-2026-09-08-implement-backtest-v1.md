---
id: OUT-2026-09-08-implement-backtest-v1
step: implement
records: [REQ-WP-010]
commit: null
---

## What was done

`channelflow.backtest`: a runner that replays finalized bars in event-time order
through `RollingOLSChannel` and `SignalMachine`, and a frozen report of what the
pass produced. 16 tests.

## What was decided

- **The runner deep-copies the machine it was given.** `SignalMachine` carries
  the live candidate, so the original runner drove the caller's machine
  directly: a second run over the same bars began mid-lifecycle and reported
  something else, and the caller's machine came back holding a candidate from
  history. FR-006 asks for two identical runs; this is what it takes.
- **Candidate identity is `opened_at_ns`, not a running index into `history`.**
  A terminal candidate is replaced rather than extended, so `history` restarts
  at length one. The first implementation tracked an index into it and silently
  swallowed the opening transition of every candidate after the first. FR-018
  forbids reopening on the bar that closed one, which is what makes the
  timestamp a sound key.
- **The lookahead guard is doubled, so it needed a test that watches the
  handover.** `RollingOLSChannel.fit` filters by `as_of` itself and the runner
  also slices the history; breaking either one alone changes no result, so no
  test noticed. `test_the_runner_never_shows_the_channel_a_future_bar` records
  what the runner passes and checks it directly.

## Mutation results

Seven mutations, all caught:

| Mutation | Caught by |
| --- | --- |
| Runner gets its own touch → confirmed rule | `test_replay_matches_the_live_engine_transition_for_transition` |
| Drop event-time ordering | `test_bars_are_replayed_in_event_time_order` |
| Replay unfinalized bars | `test_unfinalized_bars_are_not_replayed` |
| Stop counting skipped bars | `test_bars_without_enough_history_are_reported_as_skipped` |
| Report grows a `win_rate` | `test_the_report_carries_no_economic_metric` |
| Show the channel the whole series | `test_the_runner_never_shows_the_channel_a_future_bar` |
| `as_of` jumps to the end of the series | `test_the_runner_never_shows_the_channel_a_future_bar` |

The last two survived until that test existed. Both are the same finding: two
guards covering one property hide each other's absence.

## What is still open

- **A confirmed candidate holds the machine indefinitely.** Found by the first
  replay: 200 bars produced one candidate. Recorded in [[ADR-010]]; `RESOLVED`
  waits on PRD §40's outcome definition, `ALERTED` on REQ-WP-008.
- Bar replay only, no costs, no walk-forward — the spec's stated assumptions.

## A gate hole this work found

Marking REQ-WP-010 `implemented` with sixteen passing tests and no
`# @trace:` marker in any source file produced `trace: clean`. R2 asks whether
tests exist; nothing asked whether what they test can be traced, so the
request-to-implementation half of the graph could be empty and the gate would
not notice.

Fixed on this branch as **R8**: `implemented` or above requires at least one
`IMPLEMENTS` edge. Mutation-checked both ways — removing the rule fails its
test, removing the markers fails the real repo's `make validate`.

R8 then immediately flagged **REQ-INFRA-002**, whose implementation is
`.github/workflows/ci.yml` and nothing else: code collection was Python-only,
so a gate defined in YAML was invisible to the graph. Collection now covers
`.github` and YAML suffixes, and the workflow carries its own marker.
