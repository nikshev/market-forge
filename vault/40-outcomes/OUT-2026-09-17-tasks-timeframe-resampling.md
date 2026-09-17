---
id: OUT-2026-09-17-tasks-timeframe-resampling
step: tasks
records: [REQ-WP-073]
commit: null
---

## What was done

Broke [[REQ-WP-073]] into 41 tasks in
`specs/117-timeframe-resampling/tasks.md`, then ran the cross-artifact analysis
over spec, plan and tasks. It found four things worth fixing, and all four are
fixed rather than noted.

## What was decided

**The analysis earned its place, which is not the usual outcome.** Two findings
were real design errors that would have reached code.

**`ResampleReport` and `ResampleResult` were two types with one job and almost
one name.** The data model defined a `ResampleReport` carrying `written`,
`skipped`, `refusals` and a `line`; the contract defined a `ResampleResult`
carrying `bars`, `refusals` and `skipped`; and no task created the first, though
one task printed its `line`. The fix is not to merge them — they are genuinely
different, and the difference matters: **the result is what the pure function
computed, the report is what the process committed.** A pass can compute ten
bars and fail to append them, and a single type would have to report that as
either ten written or zero computed, both false. Both are now defined side by
side, with that sentence attached, and `T031a`/`T031b` build and test the
second.

**SC-005 asked for something this feature cannot deliver.** It read "a chart
opened at each configured timeframe shows candles", which is false until
[[REQ-WP-074]] wires `tf` into the request. Left alone it would have made this
requirement's completion depend on another requirement's code — so a correct,
finished resampler would have looked unfinished, and the temptation would have
been to fix the chart here, under a requirement that does not cover it. SC-005
now asks what this feature can actually be held to: the API answering for each
configured timeframe.

**FR-002's frontend clause now names its own boundary.** "No component may carry
the set as a constant — not the frontend" is right and is not this requirement's
work: §28 lists no endpoint carrying the set, and inventing one here would be an
API decision taken away from the view that needs it. The clause now says so, and
adds the obligation this feature does carry — not to satisfy it quietly with a
second list.

**`SOURCE_TOKEN` was in the contract and in no task.** Folded into T004. Small,
and exactly the kind of thing that becomes "why does this constant exist" three
months later.

**What the analysis did not flag, correctly.** The task phases run User Story 2
before User Story 1, which inverts the spec's own order. That is deliberate and
written down: US1 is the fold plus plumbing, and a wrong fold plumbed correctly
is worse than no fold. The ordering rule only fires on a contradiction *without*
a dependency note, and the note is there.

## What is still open

- **T034 asserts a property of the source tree**, by grepping for a hard-coded
  timeframe set rather than by exercising one. That is the only way to check
  FR-002's real content, which is about where a set is *not* — no runtime
  assertion can observe an absence. It is also brittle in a way runtime tests
  are not, and the first person to rename a constant will meet it.
- **Nothing in the 41 tasks runs against a live service.** That is by design and
  keeps the feature in the fast gate, but it means the only proof the running
  deployment benefits is T037's manual quickstart pass, which no gate enforces.
- **Backfill remains unaddressed**, as it was after planning. The tasks build a
  loop that catches up from wherever it starts; nothing walks history.
