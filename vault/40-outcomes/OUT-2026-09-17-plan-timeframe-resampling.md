---
id: OUT-2026-09-17-plan-timeframe-resampling
step: plan
records: [REQ-WP-073]
commit: null
---

## What was done

Planned [[REQ-WP-073]] as `specs/117-timeframe-resampling/` — plan, research,
data model, one contract, quickstart. The three questions the spec left open are
answered below; the fourth, backfill, is still open and is named as such.

## What was decided

**Idempotence is the producer's job, because nothing below it will do it.**
Planning measured `BarSink.flush` as a bare `self.table.append(self._buffer)`,
and `IcebergTable` offers `read`, `append` and `delete_rows_before` — no upsert,
no delete-by-key, no predicate pushdown. A second resampling pass would append a
duplicate of every bar and no layer would object. So each pass reads the open
times already stored for its target and produces only what is missing.

A **stored watermark** was the cheap alternative and was rejected for a reason
the spec had already created: a late minute is allowed to complete its window,
and a window behind a watermark could never be filled. Every restart would leave
a permanent hole shaped exactly like a quiet market. **Delete-and-rewrite** was
rejected for violating Constitution III on every pass — it would make the one
destructive operation in this system routine.

The read costs a whole-table scan, measured on the running stack at **89 rows in
132ms**. [[REQ-WP-068]] measured the same shape at 717 files: 6478ms before
compaction, 45ms after, and compaction already runs on a loop. The cost is
bounded by machinery that exists, which is why Principle XII is satisfied by
naming it rather than by optimising it now.

**Alignment is an origin, not a special case.** `Timeframe` carries `ns` *and*
`origin_ns`, and `window_start` is `((t - origin) // ns) * ns + origin`. Every
timeframe but the week has `origin_ns = 0`, where this is exactly the existing
expression. Verified rather than assumed:

    2026-09-14T00:00:00Z   naive = 2026-09-10 Thu   with origin = 2026-09-14 Mon

Putting the correction in the caller was rejected — that is how the second
caller gets it wrong.

**Planning found a language dependency worth a test.** For an instant before the
origin the expression is correct only because Python's `//` rounds toward
negative infinity; a truncating division would give a Thursday again. No stored
bar can reach that case — `Bar.open_time_ns` is `Field(ge=0)` — but the same
function is destined for the markets view, in TypeScript, where `Math.trunc` is
the obvious spelling. The property is pinned by a test rather than by a comment.

**`vwap` is the one field that is not a sum or an end value.** A mean of five
means is not the mean of the whole unless every minute carries equal volume.
Recomputed from the summed quote and base volumes, matching `builder.py:176`
including its zero-volume fallback to `close`, so a resampled bar and a
builder-produced bar of the same window agree. A test uses minutes of unequal
volume, because averaging the averages produces a plausible number.

**A process of its own, not a corner of `maintenance`.** That service prunes,
compacts and expires — it removes. A producer of canonical rows inside it would
be invisible to whoever reads the compose file next. The cost is a tenth
service, recorded rather than waved away. Running it inside the ingest daemon
was rejected for coupling a socket-paced process to a whole-table read;
resampling on read was rejected because it would make §29.4's `timeframe` column
mean nothing.

**Calendar periods are refused at the parser.** `1M` never reaches the
resampler: there is no `Timeframe` value for a month, so no later code can hold
one. One refusal covers configuration, a future API parameter and anything else
that parses a token.

## What is still open

- **Backfill is still unaddressed.** The design is idempotent and therefore safe
  to run over history, but nothing schedules a pass over what already exists —
  the loop only ever catches up from wherever it starts. Today the table holds
  one day, so this is cheap; it will not stay cheap, and the spec said so too.
- **How the frontend learns the configured set.** FR-002 forbids it holding its
  own copy, and §28 lists no endpoint that carries one. Deliberately deferred to
  [[REQ-WP-075]], the requirement that needs it, rather than inventing an API
  surface here.
- **The refusal is stdout only.** The contract prints every refusal, which
  satisfies FR-005's "visible to the caller". Whether it should also be a
  §33 metric is a real question and is not answered; PRD §33's list already has
  nine metrics with no producer ([[REQ-WP-055]]), so adding one without a
  dashboard would repeat that.
- **Nothing yet proves the running deployment benefits.** The quickstart can
  show 15m bars over the API, but the chart will still be empty until
  [[REQ-WP-074]] wires `tf` into the request. Stated in the quickstart so a
  reader does not read that emptiness as this feature failing.
