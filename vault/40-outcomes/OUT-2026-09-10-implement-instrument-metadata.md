---
id: OUT-2026-09-10-implement-instrument-metadata
step: implement
records: [REQ-WP-021, REQ-PHASE-1]
commit: null
---

## What was done

`domain/instrument.py` (the value and its refusals),
`connectors/binance/instruments.py` (the venue's dialect, stopped at the
boundary), the `markets` table widened by seven columns, and both repositories
serving an instrument with its market.

1534 fast tests, mypy clean at 166 files, 14 of 14 mutants caught.

[[REQ-PHASE-1]]'s last unbuilt deliverable is closed and the phase reaches
`implemented` — the third, after [[REQ-PHASE-6]] and [[REQ-PHASE-0]].

**The plan and implement rungs share this commit.** The pre-commit gate runs the
real suite, and a tree with only half a change staged does not compile — the
same reason CLAUDE.md already gives for `tested` sharing a commit with the
implementation. The plan artifacts and their outcome note are here in full and
were written before the code.

## What the work found

- **A decimal column reads back as the string `"0"` on some paths, and `not "0"`
  is `False`.** The first `instrument_from_row` tested the raw value for
  truthiness, so a market stored without rules was reconstructed as an
  instrument and refused on its empty base asset. Four API tests went red. The
  check is numeric now, and the reason is in the code beside it.
- **"Missing" and "zero" were indistinguishable to the test.** Defaulting a
  missing filter to `Decimal(0)` still raises — the value object refuses it —
  but reports "tick_size is 0", and a reader would go looking for a zero in the
  payload that is not there. The mutation sweep found the test could not tell
  the two apart; it now asserts the word.
- **A float in the payload would have been converted, not refused.** The tests
  fed strings, as Binance does, so nothing exercised the path where something
  upstream had already parsed the JSON with float numbers. `Decimal(0.1)` is not
  refused by Python and is not the venue's tick size.

## What was decided

- **Refusal lives in the constructor**, so no consumer has to remember and no
  path — normalizer, fixture, stored row, second venue — can produce a rule that
  would round a price to nothing.
- **A spot instrument has no contract size.** A `1` would let a later
  calculation multiply by it and be right by accident, which survives review in
  a way that being wrong does not.
- **The latest row wins for a market described twice**, on both implementations,
  so a routine re-ingest does not read as a second venue.

## What is still open

- **Nothing uses the rules yet, and that is the boundary this requirement drew.**
  Rounding a fill to a valid tick, refusing a size under the minimum and skipping
  a halted instrument each change the backtest's execution model, and each wants
  its own requirement. PRD §41 rule 9 is the reason they matter; the numbers are
  now there for whoever writes it.
- **Only Binance's shape is normalized**, because it is the only connector.
  Whether `Instrument` survives contact with a venue that expresses its rules
  differently is not knowable from one example.
- **The `markets` schema fingerprint changed.** Nothing cites that table in a
  dataset reference today, so nothing was invalidated — true now rather than by
  design.
