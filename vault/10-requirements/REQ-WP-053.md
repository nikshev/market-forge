---
id: REQ-WP-053
title: The DeFi primitives land on the canonical plane
type: work-package
prd_ref: "§18.12, §6.4, §45 Phase 4"
prd_lines: "3147-3240, 440-450, 6793-6794"
phase: 4
status: implemented
depends_on: [REQ-WP-015, REQ-WP-039]
tags: []
---

## Requirement

PRD §18.12 asks protocol adapters to emit "common **economic primitives**, not a
fake common state model", and §6.4 makes Iceberg the canonical analytical
history. The adapters have produced those primitives since [[REQ-WP-015]] and
nothing has stored them: the plane has been Iceberg since [[REQ-WP-039]] and
carries no DeFi table.

Three of §18.12's four primitives have producers today:

- **§18.12.1 `NormalizedSwap`** — the v3 reducer's swaps.
- **§18.12.4 `LiquidityChange`** — its mints, burns and collects.
- **§18.12.3 `ExecutableDepthCurve`** — the depth walk's bands.

**§18.12.2 `LiquidityState` has none**, and is not defined here. Its
`reconstruction_quality` and `model_type` describe a reconstruction nothing
performs yet, and a table nothing writes is a schema pretending to be a
guarantee.

**A depth curve is a curve and a table holds rows**, so it flattens to one row
per pool, per side, per band. §18.12.3's bands are "configurable by liquidity
regime", so the band is a column: a schema with one column per band needs a
migration the first time a regime wants a different grid.

**[[ADR-036]]'s `reachable` must survive as a column.** When it is false the
amounts describe *exhausting* the known liquidity rather than reaching the
target. Both rows carry a notional and a band, and without the flag a pool too
thin to move 100 bps reads as a pool where 100 bps is cheap — the more dangerous
of the two directions.

## Acceptance

- Swaps, liquidity changes and depth curves each have a canonical table, and a
  row written through it comes back identical.
- Amounts keep their signs, which is what says which way a swap went and whether
  liquidity was added or removed.
- Values beyond `int64` — `sqrt_price_x96`, `liquidity`, `liquidity_delta` —
  survive, and a test shows the values used exceed it.
- Prices keep every digit, and a test shows the value used is one `float64`
  cannot hold.
- A field with no producer is absent from the schema rather than null on every
  row, and a test names the five §18.12.1 fields left out and why.
- A field that is *sometimes* absent stores as absent, and is distinguishable
  from zero and from empty.
- An unreachable depth band is distinguishable from a cheap one.
- Both sides of a depth curve keep their own tokens; no conversion happens at
  write time.
- A point-in-time read excludes rows whose event time is later.

## Notes

Human territory. Never machine-rewritten.

**This exposed a defect in the plane itself.** No canonical table had ever
written a null, so the row encoder had no representation for one and the Arrow
conversion stringified it into the literal text `"None"`. [[ADR-066]] records the
fix and why it leaves every existing content hash where it was.

**`price_before` and `price_after` are absent together.** §18.12.1 marks both
nullable and the reducer emits the price a swap left behind rather than the pair;
storing one under a name implying both is worse than storing neither.
