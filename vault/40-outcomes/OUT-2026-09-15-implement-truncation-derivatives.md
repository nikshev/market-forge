---
id: OUT-2026-09-15-implement-truncation-derivatives
step: implement
records: [REQ-NRT-LEAK]
commit: null
---

## What was done

Covered `derivatives` (19) for PRD §35.4. **33 of 55** features now have
truncation cases; 22 remain. [[REQ-NRT-LEAK]] stays at `tested`.

- `tests/unit/features/test_truncation_parity.py` — nineteen new cases.
- `tests/mutations/truncation_derivatives.toml`,
  `tests/mutations/truncation_liquidations.toml`.

## What was decided

**Five of the nineteen have no dataset to truncate, and that is the interesting
part.** `basis_bps(perp_price, spot_price)`, `mark_premium_bps`, `oi_to_volume`,
`price_oi_regime` and `liquidation_intensity_5m` are pure functions of already
selected scalars. §35.4 says "run on truncated dataset / run on full dataset",
and these have neither — a case handing them two constants would agree with
itself and report coverage.

So their arguments are sourced through `state_at`, the package's point-in-time
seam, which filters `event_time_ns <= at_ns`. That is where a leak in these
features would actually live: not in the arithmetic, in the selection. The
refusal mechanism was the obvious alternative and would have been wrong — these
features *can* be checked, just not at the boundary the signature suggests.

**A constant denominator, deliberately.** `oi_to_volume` and
`liquidation_intensity_5m` take a traded volume that is not point-in-time data
here. It is a constant so that any disagreement the case reports comes from the
numerator's selection rather than from the fixture.

**The cases discriminate — five mutations, five caught.** Against the truncation
suite alone:

| mutation | result |
|---|---|
| the point-in-time seam stops filtering on `at_ns` | caught |
| the seam takes the newest state rather than the newest at or before `at_ns` | caught |
| **the seam reads ingest time instead of event time** | caught |
| the liquidation window reaches past `as_of` | caught |
| time since spike looks at events after `as_of` | caught |

The third is the one worth noting. Reading `ingest_time_ns` where
`event_time_ns` belongs is a real and subtle leak — a correction that arrives
late describes an old instant, and an ingest-time filter lets it count as
current. `state_at`'s own docstring says age is measured from event time; now
something fails when it is not.

### Two corrections, both mine

- `liquidation(side="long")` — the literal is `"long_liquidated"`. Caught at
  collection.
- `test_every_case_computes_a_number` rejected `price_oi_regime`, which returns
  a `StrEnum`. A classification is a value, and a leak in it reads as the wrong
  regime rather than the wrong magnitude. Renamed and widened to accept a string.

## What is still open

**22 features**: `order_book` 15, `volume_structure` 5, `defi` 2.

**Three family shapes measured now**, and `derivatives` was the first to contain
more than one: `(states, *, at_ns, ...)` for fourteen of its nineteen, and pure
scalars sourced through a seam for the other five. `order_book` goes through a
`BookService`, which is a fourth shape and the last large one.
