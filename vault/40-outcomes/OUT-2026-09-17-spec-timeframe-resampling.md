---
id: OUT-2026-09-17-spec-timeframe-resampling
step: spec
records: [REQ-WP-073]
commit: null
---

## What was done

Specified [[REQ-WP-073]] as `specs/117-timeframe-resampling/spec.md`. The
requirement came from a request for a dashboard with a timeframe selector; the
selector has nothing to select until the series exist, so this is the first rung
of four.

## What was decided

**Higher timeframes are built from the stored minutes, not by a second builder.**
`BarBuilder`'s docstring names the alternative — "One symbol, one timeframe.
Composition of several is the caller's" — so running one builder per timeframe
against the trade stream is the path the code was shaped for. Resampling was
chosen instead because it is idempotent, can be run over already-archived
history, and adds nothing to the socket-side path. The decision is recorded with
its cost rather than as a preference.

**That cost is a new failure mode, and it gets its own constraint.** A resampler's
input can be *incomplete without being late*: a window missing three of its 240
minutes is indistinguishable from a complete one unless something counts. The
trade-driven builder cannot have this problem, because a watermark tells it time
moved on. [[REQ-NRT-UPSAMPLE]] is `hard_gated`, so R5 forbids it a status past
`specified` without a test — which is the intended shape for a rule that a
plausible implementation violates silently.

**Every timeframe is built from minutes, never from another resampled timeframe.**
Chaining 1m → 5m → 15m → 1h would compound both error and incompleteness: one
missing minute would silently poison every level above it, and the level that
refused would not be the level that was wrong. Flat construction costs more reads
and makes each window's completeness a local question.

**A week opens Monday, and this had to be said out loud.** `(t // tf) * tf`
aligns to the Unix epoch, and 1 January 1970 was a Thursday, so the obvious
implementation produces weekly bars opening on Thursdays. Nothing would fail;
the chart would simply be wrong in a way that looks like a data problem. The
acceptance criterion is therefore a window containing a Thursday, not a window
chosen for convenience.

**`1M` is refused, not approximated.** A calendar month is 28–31 days and
`timeframe_ns` is `int64` nanoseconds, so there is no value to store. Accepting
2592000e9 as "a month" would drift against the calendar and be visible to nobody
reading the chart. The refusal must name the reason, so the next person to want
monthly bars finds the problem rather than the gap.

**A missing minute that arrives later may complete its window.** No bar for that
window was ever published, so producing one then is not an amendment and
Constitution III is untouched. Stated in the spec because the opposite reading —
that a window once skipped is skipped forever — is equally defensible and would
have produced permanent holes after every restart.

## What is still open

- **Where the resampler runs.** The `maintenance` service already loops on an
  interval and would be the obvious host, but a producer of canonical rows
  sitting inside a service named for pruning and compaction is a naming problem
  at least. Deliberately left to `/sdd-plan`.
- **What the configuration surface looks like.** Today there is one
  `CHANNELFLOW_INGEST_TIMEFRAME_NS`; §31 describes a `timeframes:` list per
  market. FR-002 requires the set to come from configuration but does not say
  whether that is an environment variable, the §31 YAML, or both.
- **Whether the refusal for an incomplete window is a log line, a metric, or a
  returned value.** FR-005 requires it to be visible to the caller; which of the
  three satisfies "visible" is a design question, and the wrong answer here is
  the one that makes the refusal as silent as the bug it replaces.
- **Backfill over existing history is not specified.** The feature is idempotent
  and therefore safe to run over history, but nothing says it will be run, or by
  what. The running deployment has minutes from 2026-09-17 only, so this is
  cheap now and will not stay cheap.
