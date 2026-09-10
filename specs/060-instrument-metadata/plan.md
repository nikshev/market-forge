# Implementation Plan: An instrument's trading rules

**Branch**: `wp-021-instrument-metadata` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

## Summary

A value, a normalizer, a widened table, and the API serving it.

The decision that shapes the rest: **`Instrument` refuses a bad rule in its own
constructor.** A tick size of zero, a negative step, a float that came through
JSON — each is rejected where the value is made rather than where it is used, so
no consumer has to remember to check and no path can produce a rule that would
round a price to nothing.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: none new.

**Storage**: the existing `markets` table, widened by seven columns.

**Testing**: pytest, `@pytest.mark.trace("REQ-WP-021")`, a mutation sweep, and the existing conformance suite over both repositories.

**Project Type**: single project.

**Constraints**: decimal end to end; no float in the path. HTTP out of scope.

**Scale/Scope**: one value type, one normalizer, one schema change, two repositories.

## Constitution Check

| Principle | Bearing | Verdict |
|---|---|---|
| **VI. Every feature is documented** | Each field's reason is in the value's docstring rather than in a spec nobody reads next to the code. | **Pass.** |
| **X. Thresholds are configuration** | These are the venue's numbers, not ours; none is hard-coded. | **Pass.** |
| **VIII. Connectors share one interface** | Binance's field names stop at `connectors/binance/`. | **Pass.** A second venue is a second normalizer producing the same value. |
| **XII. Correctness precedes performance** | A read that dedups by key rather than returning rows. | **Pass.** |

No violations.

## Project Structure

```text
src/channelflow/domain/instrument.py            # NEW: Instrument, InstrumentRejected
src/channelflow/connectors/binance/instruments.py  # NEW: instruments_from
src/channelflow/tables/features.py              # markets schema + market_row/instrument_from_row
src/channelflow/api/repositories.py             # Market.instrument; add_market keyed
src/channelflow/api/lakehouse_repository.py     # latest row per market wins
tests/unit/domain/test_instrument.py            # NEW
tests/unit/connectors/binance/test_instruments.py  # NEW
tests/unit/api/test_repository_conformance.py   # + six, over both implementations
```

**Structure Decision**: the value lives in `domain/` with the other things the
whole system shares; the venue's dialect lives in `connectors/binance/`, which
is where [[REQ-WP-003]] already keeps it.
