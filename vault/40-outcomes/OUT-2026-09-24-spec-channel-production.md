---
id: OUT-2026-09-24-spec-channel-production
step: spec
records: [REQ-WP-077]
commit: null
---

## What was done

[[REQ-WP-077]] specified as `specs/122-channel-production/spec.md`.
`traces: [REQ-WP-077]`; requirement note visible as
[[SPEC-122-channel-production]].

## What was decided

**Nothing new is fitted.** `record_replay` already reads bars and writes
channel snapshots, signals, confirmed extrema and extremum candidates, and the
spec keeps it that way: the missing piece is a process that drives the
function that exists over the bars the deployment already has. An alternative
that re-implements the fit inside a daemon was never on the table — it would
be a second path for live data to take, and Principle VII forbids exactly
that.

**The pass is per timeframe, driven by the resampler's configuration.** A
channel at 4h is a fit over 4h bars, so the pass reads whatever
`CHANNELFLOW_TIMEFRAMES` names. The timeframe list is not repeated in a second
variable: [[REQ-WP-073]] owns it, and a list here would be the kind of
parallel configuration that drifts.

**Idempotence is verified, not inherited.** Every recorder in `replay.py`
carries a watermark, but a loop running every few minutes over a growing
series is not the same exercise as a single replay over a fixture. FR-003
requires row counts before and after a second pass, and the watermarks are the
mechanism, not the proof.

**One timeframe failing does not end the pass.** The failure names its venue,
symbol and timeframe, and the rest complete — the rule `maintenance_main`
already follows. A pass that stopped at the first refusal would leave every
later timeframe unproduced for a reason that has nothing to do with them.

**Missing bars are a skip, not a failure.** A configured timeframe with no
series yet (a week that has not closed, a symbol that just started) is logged
and left for a later pass. Failing the pass would turn an ordinary young
deployment into an incident.

**Snapshots are never rewritten.** Constitution III and §29.6's immutable
append-only hold for a loop exactly as they hold for a fixture: a pass that
re-fits an already-recorded moment must not replace it.

**Signals stay final-state-only under loop frequency.** [[REQ-PIPE-001]]
established that a signal reaches the table once, in its final state; a loop
invokes that path far more often than a fixture does, so FR-007 re-checks it
here rather than citing it.

## Gate repair outside this feature, recorded

`make validate` failed on a stale committed mutation sweep, not on this spec:
[[REQ-WP-076]] renamed `session.transport` to `session.connector`, and two
mutation anchors still named the old attribute — "stopping closes before it
commits" in `tests/mutations/ingest.toml` and "a server ping is not answered"
in `tests/mutations/session.toml`. Both anchors were updated mechanically
(`transport` → `connector`), preserving each mutation's intent. The sweep is
the property that stops a skipped test from satisfying a coverage rule, so a
red sweep blocks every commit until fixed, whatever step owns the commit.

The same `make graph` run surfaced a second [[REQ-WP-076]] leftover: rewriting
`connectors/{binance,bybit,okx}/__init__.py` had replaced their original trace
markers instead of adding to them, silently dropping the code links of
[[REQ-WP-003]], [[REQ-WP-043]] and [[REQ-WP-044]]. The files still export the
normalize symbols, so they still implement those requirements — the old markers
were restored alongside `# @trace: REQ-WP-076`. One file may carry more than
one marker; replacing instead of adding is how a link is lost without any rule
firing, because the orphaned requirements still had other code files.

## What is still open

- **How the pass is scheduled.** Loop inside a long-lived process, cron-shaped
  invocations, or a step inside an existing service — planning's decision. The
  spec fixes the behaviour (per timeframe, skip-and-log, named failures), not
  the mechanism.
- **Whether the pass is its own service.** The requirement descends from §6.2's
  `worker`, but whether that means a container, a step in the resampler, or a
  corner of maintenance is planning's, with the plan's "a producer hidden
  inside maintenance" warning from [[REQ-WP-073]] on the record.
- **Which (venue, symbol) pairs are covered.** The bars table already knows
  which series exist; whether the pass discovers them or takes a list is
  planning's.
