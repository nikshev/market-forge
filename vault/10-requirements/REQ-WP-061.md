---
id: REQ-WP-061
title: A nanosecond survives the trip to the browser
type: work-package
prd_ref: "§28, §13A.1, §41"
prd_lines: "4461-4530, 1260-1272, 5315-5330"
phase: null
status: implemented
depends_on: [REQ-WP-009, REQ-WP-054]
tags: []
---

## Requirement

Every time this system serves is a nanosecond count since the epoch, so around
1.8e18. JavaScript's `number` is an IEEE-754 double and
`Number.MAX_SAFE_INTEGER` is 9.0e15 — about two hundred times smaller. At the
magnitude of a real timestamp the representable values are **256 nanoseconds
apart**, so a mark read as a number is rounded and two marks 100 nanoseconds
apart compare equal. Measured:

    served   1789000000123456789
    read     1789000000123456768      shifted by 21 ns
    grid step at that magnitude        256 ns
    Number(1789000000000005000n) === Number(1789000000000005100n)   true

Fourteen of the sixteen `_ns` fields in the web app are `number`. The two that
are not are `DexDepthResponse`'s, added by [[REQ-WP-054]] and recorded there as
an open question about the rest.

### Why it is a correctness matter and not tidiness

PRD §13A.1 requires two times to be stored for every extremum —
`extremum_time` and `known_at`, "first timestamp when the system was legally able
to know" — and states `extremum_time != known_at`. The comparisons that enforce
that are the ones the rounding reaches:

    extrema.ts       e.known_at_ns <= atNs          admits what was knowable
    extrema.ts       c.observed_at_ns <= atNs       the same, for candidates
    stopPath.ts      anchor.known_at_ns > p.at_ns   refuses an impossible stop
    panes.ts         Map keyed by at_ns             two points, one key

**Every one of them errs in the permissive direction.** A fact that became
knowable 100 nanoseconds *after* the cursor compares equal and is admitted; the
guard whose whole job is to catch a stop anchored on later knowledge has a
256-nanosecond blind spot; and two feature points closer than that collide into
one map key where the documented rule — last write wins, for a correction —
silently drops one. Constitution Principle I is the rule none of this may bend,
and `make validate` cannot see any of it.

**It is latent, not a wrong number on screen today.** Present sources timestamp
in milliseconds or microseconds, and logs of one block share `block_time_ns`
exactly, so two distinct marks within 256 nanoseconds do not currently arise.
This is a guard with a blind spot rather than an observed defect, and the cost of
leaving it grows with every consumer of these fields.

### Timestamps, not durations

A timestamp since the epoch is unsafe always. A duration is not: `timeframe_ns`
and `hindsight_ns` are bounded by the timeframes this system supports, and a week
is 6.0e14 — comfortably inside the safe range. They stay numbers, with the bound
asserted rather than assumed, because converting them would be churn that
obscures which fields had a reason.

### `BigInt("")` is `0n`

Not an error. An empty or absent field becomes the epoch — 1970 — which is
positive, ordered and believable, and would place a bar or a signal at the
beginning of time rather than failing. Conversion therefore rejects anything that
is not a run of digits, and it happens inside `api.ts`'s `Result` boundary, where
REQ-WP-009's FR-016 already requires that a bad load be stated rather than
rendered.

## Acceptance

- Every timestamp field the API serves is a string on the wire; every duration
  field stays an integer, and a test names which is which so a new field has to
  choose deliberately.
- The web app holds every timestamp as `bigint` and every comparison that decides
  knowability is `bigint` arithmetic.
- A round trip of a timestamp whose low digits are not a multiple of 256 returns
  the exact value, asserted against the value read as a number.
- Two marks 100 nanoseconds apart remain distinct through the API, the client and
  the pane's map.
- A timestamp field that is empty, absent, negative, fractional or non-numeric
  produces a failed load, not the epoch and not a render.
- The conversion to `number` for the chart's axis happens in one named place, and
  the loss is stated there rather than implied by a coercion.
- The duration bound is asserted: a timeframe expressible by this system stays
  inside `Number.MAX_SAFE_INTEGER`.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-102-nanosecond-precision]]
- **Tests:**
    - `tests/unit/api/test_wire_time.py::test_a_mark_survives_json_exactly_where_a_number_would_not`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[ 1789]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[+5]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[-1]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[007]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[0x10]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[12.5]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[1789 ]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[1e9]`
    - `tests/unit/api/test_wire_time.py::test_a_timestamp_that_is_not_digits_is_refused[abc]`
    - `tests/unit/api/test_wire_time.py::test_an_empty_timestamp_is_refused_rather_than_becoming_the_epoch`
    - `tests/unit/api/test_wire_time.py::test_durations_stay_integers_and_fit_in_a_double`
    - `tests/unit/api/test_wire_time.py::test_every_ns_field_is_a_timestamp_or_a_duration`
    - `tests/unit/api/test_wire_time.py::test_timestamps_go_over_the_wire_as_strings`
    - `tests/unit/api/test_wire_time.py::test_two_marks_closer_than_the_double_grid_stay_distinct`
    - `tests/unit/api/test_wire_time.py::test_zero_is_a_valid_mark`
- **Code:**
    - `apps/web/src/__tests__/api.test.ts`
    - `apps/web/src/__tests__/time.test.ts`
    - `apps/web/src/time.ts`
- **Outcomes:** [[OUT-2026-09-13-implement-nanosecond-precision]]
<!-- trace:end -->

## Notes

This changes the wire format of eleven fields. The web app in this repository is
the only consumer, so nothing outside it breaks; a version bump is not part of
this requirement because §28's routes are unversioned in the PRD beyond
`/api/v1`, and no second client exists to be broken.

`PositionOut`, `StopProposalOut` and `StopAnchorOut` are mirrored from
`stops/models.py` and served by no route yet ([[REQ-WP-032]]). Their timestamps
are converted here anyway, because `stopPath.ts`'s look-ahead guard is one of the
four sites above — and the route that eventually serves them has to match a
declaration that already says string.
