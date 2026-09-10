# Phase 0 — Research

## 1. Where does a bad rule get refused?

**Decision**: in `Instrument.__post_init__`.

**Rationale**: a rule is used by code far from where it was parsed. Validating
at the point of use means every consumer remembers to, and the one that forgets
rounds a price to a tick of zero and produces a number. Validating in the
constructor means the bad value never exists.

**Alternatives considered**: validate in the normalizer only. Leaves every other
construction path — a test fixture, a second venue, a row read back — free to
build a nonsense instrument.

## 2. How is "no rules yet" stored, on a plane with no null?

**Decision**: empty strings and a zero tick size on the row; `instrument_from_row`
returns `None` when the tick size is not positive.

**Rationale**: `add_market` without rules must still write a schema-valid row.
Zero is the one value `Instrument` itself refuses, which makes it unambiguous as
a marker — a row carrying it cannot be a real instrument.

**What this cost**: the first implementation tested the raw value for
truthiness, and a decimal column reads back as the string `"0"` on some paths,
which is truthy. Four API tests went red on an empty base asset. The check is
numeric now.

## 3. A market described twice

**Decision**: the latest row wins, on both implementations.

**Rationale**: the plane is append-only, so a re-ingest is two rows. Returning
both would make a routine refresh look like a second venue. This is the reading
the scores table already uses. The in-memory repository is keyed by
`(venue, symbol)` so the two implementations cannot drift.
