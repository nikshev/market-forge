---
id: OUT-2026-09-15-implement-truncation-order-book
step: implement
records: [REQ-NRT-LEAK]
commit: null
---

## What was done

Covered `order_book` (15) for PRD §35.4 — **4 cases and 11 refusals** — and fixed
the first real leak this requirement has found.

**48 of 55** features are now accounted for: 37 cases, 11 refusals, 7
outstanding (`volume_structure` 5, `defi` 2). [[REQ-NRT-LEAK]] stays at `tested`.

## The leak

`WallTracker.observe(service, *, trades, as_of_ns)` takes the data and the moment
**separately**, and reconciled them nowhere. Handing it the whole day's trades
with an earlier `as_of_ns` attributed future volume to a wall's execution.
Measured on a wall shrinking three units a step against trades of 0.2 each:

| | filtered to `as_of_ns` | whole stream handed over |
|---|---|---|
| `executed_size_est` | 2.0 | **4.0** |
| `cancelled_size_est` | 25.0 | **23.0** |

Two registered features, both declaring `point_in_time_safe: True`, could be
given a value that depends on data after `t` — through a call the signature
permits. No production caller did it; nothing stopped one.

`observe` now ignores trades after `as_of_ns`. The argument is the one
`state_at`'s docstring already makes: a rule each call site has to remember is a
rule one call site will forget.

**Trade size is why an earlier attempt saw nothing.** At one unit a trade the
attribution saturates against the wall's shrink and both runs agree — for a
reason that has nothing to do with point-in-time safety. The first measurement
came back `DIFFERENT=False` and looked like proof of correctness. It was proof of
a badly chosen fixture. The test now asserts that volume was actually attributed,
so it cannot pass in the saturated regime.

## What was decided

**Eleven instant features are refused, and the reason is true.** `qi_l1`,
`microprice`, `microprice_mid_spread_bps` and the eight depth imbalances read
`BookService` as it stands. No API in that path accepts a dataset **and** a
moment, so §35.4's second run has no expression: the only way to ask for `t` is
to have replayed exactly to `t`, which makes the two runs one run.

I spent some effort trying to avoid this — including, briefly, adding a dead
module-level list to `src/channelflow/features/instant.py` so a mutation could
inject a working leak. That was wrong twice over: production code carrying
scaffolding for a test tool, and a proof of discrimination that would have been
manufactured rather than found. Reverted.

**My spec said refusals would be rare. That expectation was wrong**, and the
right response is to record it rather than bend the facts. A fifth of the
registry cannot be asked this question, because the question needs an API that
takes a moment and eleven features have none. The refusal makes that visible in
the suite's own output, which is what the mechanism is for.

**A mutation caught for the wrong reason is not a catch.** The first
`order_book` mutation referenced `_top` where the source says `service.top(1)`.
It raised `NameError`, the sweep reported `caught`, and it proved nothing.
`tools/mutate.py` refuses a mutation that breaks the *import*; a runtime
`NameError` it cannot see. Worth knowing.

## What is still open

**7 features**: `volume_structure` 5, `defi` 2. One cycle.

**Whether the eleven refusals should become cases** if a point-in-time read is
ever added to `BookService` — `service.health(as_of_ns)` already takes one, so
the shape is not foreign to the class.
