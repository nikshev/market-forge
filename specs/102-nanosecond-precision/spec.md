---
traces: [REQ-WP-061]
status: draft
---

# Feature Specification: A nanosecond survives the trip to the browser

**Feature Branch**: `wp-061-nanosecond-precision`

**Created**: 2026-09-13

**Status**: Draft

**Input**: REQ-WP-061 — the `_ns` fields the API serves and the web app reads.

## Context

A nanosecond mark is around 1.8e18; `Number.MAX_SAFE_INTEGER` is 9.0e15. At that
magnitude the representable doubles are 256 nanoseconds apart, so a mark read as
a `number` is rounded and two marks 100 nanoseconds apart compare equal.
Fourteen of sixteen `_ns` fields in the web app were numbers.

PRD §13A.1 requires `extremum_time != known_at`, and the comparisons that enforce
it are exactly the ones the rounding reaches — always permissively.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A turn that was not knowable stays hidden (Priority: P1)

An extremum became knowable 100 nanoseconds after the chart's cursor.

**Acceptance**: it is not drawn. As numbers the two instants were equal and `<=`
admitted it.

### User Story 2 - Two feature points remain two (Priority: P1)

**Acceptance**: `paneSeries` returns both. Keyed as numbers they were one key,
and the "last write wins" rule — written for a correction — dropped one.

### User Story 3 - A bad time is a stated failure (Priority: P1)

The API sends `""`, `"12.5"` or `"abc"` in a `_ns` field.

**Acceptance**: the load fails with the field named. Not the epoch, and not an
exception inside a render.

### User Story 4 - The cursor goes out exactly (Priority: P2)

**Acceptance**: `as_of_ns` in the query string is the instant the chart shows,
digit for digit.

### Edge Cases

- `BigInt("")` is `0n` — the epoch, believable and wrong.
- `"007"` is refused: two spellings of one instant must not both be servable.
- A duration is a number on purpose; a week is 6.0e14, inside the safe range.
- `state_time_ns` may legitimately be null.
- `Date.parse(iso) * 1e6` in floating point lands back above the safe range.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every timestamp the API serves is a digit string; `WireTime`
  refuses empty, negative, fractional and leading-zero forms at the schema.
- **FR-002**: Durations stay integers, and a test names which fields are which.
- **FR-003**: The web app converts every `_ns` string to `bigint` in `api.ts`,
  inside the `Result` boundary.
- **FR-004**: A `_ns` number is treated as a duration and left alone — the rule
  the Python contract test makes safe.
- **FR-005**: Every knowability comparison is `bigint` arithmetic.
- **FR-006**: `Map` keys for instants are `bigint`.
- **FR-007**: Narrowing to `number` happens only in `chartSeconds` and
  `chartMilliseconds`, both dividing in `bigint` first.
- **FR-008**: Outgoing instants are `bigint` and stringified exactly.

### Key Entities

- **WireTime** — the schema-level contract for an instant on the wire.
- **time.ts** — `nanoseconds`, `duration`, `chartSeconds`, `chartMilliseconds`,
  `nanosecondsFromIso`, `BadTime`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 1789000000123456789 round-trips exactly; the same value through a
  double is 1789000000123456768.
- **SC-002**: Two marks 100 nanoseconds apart stay distinct through the API, the
  client, the pane's map and the extrema filter.
- **SC-003**: Each of eight malformed forms produces a failed load naming the
  field.
- **SC-004**: Mutating the pattern, reverting a field to `int`, dropping a
  `str()` or converting a duration is caught by a test.

## Assumptions

- The web app is the only consumer of these routes, so changing eleven fields'
  wire format breaks nothing outside this repository.

## Open Questions

- `PositionOut` and the stop shapes are converted here but served by no route
  yet; the route that serves them must match a declaration that already says
  string.
