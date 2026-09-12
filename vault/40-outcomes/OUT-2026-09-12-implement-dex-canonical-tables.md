---
id: OUT-2026-09-12-implement-dex-canonical-tables
step: implement
records: [REQ-WP-053]
commit: null
---

## What was done

`tables/dex_swaps.py`, `tables/dex_liquidity.py`, `tables/dex_depth.py`, a fix to
the lakehouse's null handling, and five mutation specifications. 21 new table
tests plus 6 in the lakehouse suite; the full sweep now stands at 224 caught, 10
survived.

## The tables were the easy half

Three of §18.12's four primitives have producers, and each became a table
following `bars.py`'s shape. The decisions worth naming:

- **Signs are the data.** §18.12.1 asks for "signed flow", and the sign *is* the
  direction — negative is out of the pool. Storing magnitudes and a side would be
  the same information in a shape that invites somebody to sum it.
- **`sqrt_price_x96`, `liquidity` and `liquidity_delta` are strings.** They are
  uint160, uint128 and int128 on chain; an `int64` column would overflow silently
  on exactly the pools with the most liquidity.
- **A curve flattens to one row per band per side**, with the band as a column.
  §18.12.3 says the grid is "configurable by liquidity regime", and a column per
  band needs a migration to change one.
- **[[ADR-036]]'s `reachable` is a column**, because both kinds of row carry a
  notional and a band. Without it a pool too thin to move 100 bps reads as a pool
  where 100 bps is cheap.
- **Depth amounts stay in their own tokens.** Converting at write time bakes in
  the reference price and makes the row unreadable at any other — and comparing
  token0 against token1 directly is the mistake that once reported every pool as
  asymmetric.

**`LiquidityState` is not defined.** Its `reconstruction_quality` and
`model_type` describe a reconstruction nothing performs, and a table nothing
writes is a schema pretending to be a guarantee.

## The half that mattered was a defect in the plane

`notional_usd` is nullable in §18.12.1, so this is the first canonical table that
has to store a null. It failed — and the failure was three layers down, reading
as `decimal.InvalidOperation` from the content hash.

**No canonical table had ever written a null.** `bars`, `signals`, `channels` and
the rest fill every field on every row, so the encoder's `TypeError` on every
type's `None` had never fired, and `_for_arrow` stringified before checking:
**a null decimal was written as the literal text `"None"`.**

It raised on read, which is the good direction. But the Parquet file was already
wrong, and PRD §6.4 plans for Trino and DuckDB reading those files directly,
where that text is exactly what they would have seen.

[[ADR-066]] records the fix: Arrow stores a real null, and the encoder marks one
with a length of `0xFFFFFFFF` — four gigabytes, against rows measured in bytes. A
length rather than a new tag, so every non-null value's bytes are unchanged and
**no content hash already in the registry moves**. 158 existing lakehouse and
table tests passing untouched is the check on that.

## What the sweep found, and it was the good kind

Two survivors, both in the null encoding, and both real:

- **An empty payload would have collided with an empty string.** `_encode`
  returns no bytes for `""` and for an empty list, so marking a null that way
  would have made "this field is empty" and "nobody recorded this field" one
  dataset. The marker is a length no payload can have for exactly this reason,
  and there is now a test that says so.
- **The type tag in front of the null was never actually checked.** The test
  compared a null in one column against a null in another, which differ by
  position anyway. Catching it needed two schemas differing only in a column's
  type, both null there.

## And the harness caught two more things

- **A specification naming two test paths in one string.** The baseline check
  refused it rather than measuring nothing, and `tests` now takes a list — which
  a mutation to a shared module needs, since it is only honestly measured against
  every suite that exercises it.
- A pattern that drifted after `ruff format`, again.

## What is still open

- **`available_at` and `finality_status` on a swap row.** They live on
  [[REQ-WP-014]]'s chain records; duplicating them would create two answers to
  one question, and joining them is a different piece of work.
- **`LiquidityState`**, when something reconstructs one.
- **The UI depth overlay**, which Phase 4 still lists and which now has a table
  to read from.
