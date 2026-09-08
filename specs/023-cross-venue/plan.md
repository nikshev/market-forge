# Implementation Plan: Cross-venue engine

**Branch**: `wp-016-cross-venue` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

## Summary

Four modules under `src/channelflow/crossvenue/`: what a venue tells the engine,
the consensus and the basis measured against it, fragmentation and best
execution, and lead-lag — the last of which nothing on the signal path may
import.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`.

**Primary Dependencies**: none new. `Decimal` for prices, `math.log` for
returns, `statistics` for the median.

**Storage**: none. Quotes are supplied per call.

**Testing**: pytest, pure. Fixtures are a Binance-shaped order book and a
Uniswap v3-shaped pool, both quoting representations that resolve to one
canonical asset through REQ-ASSET-001's registry.

**Target Platform**: `src/channelflow/crossvenue/`.

**Constraints**: FR-008 ([[ADR-039]]), FR-011 ([[ADR-040]]), FR-015 and FR-016
(no clock; every instant is an argument).

**Scale/Scope**: 4 modules, 36 tests.

## Constitution Check

- **I (no look-ahead)** — every return window is closed at the instant asked
  about, and a window reaching before the data start returns nothing rather
  than a return computed over a shorter span and labelled as the longer one.
- **VI (every feature is documented)** — a consensus names its contributors and
  their count, so a reader can say which venues the figure rests on.
- **X (thresholds are configuration)** — the staleness tolerance and the depth
  bands are arguments with defaults, not constants in the arithmetic.
- **XI (results are reproducible)** — ties in the best-execution ranking break
  on venue id, so two runs over one input agree.
- **XIV** — traces to REQ-WP-016.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/crossvenue/
├── __init__.py        # re-exports consensus and fragmentation -- NOT leadlag
├── models.py          # VenueQuote, ExecutableQuote
├── consensus.py       # consensus_mid, basis_bps, executable_basis_bps
├── fragmentation.py   # depth_table, best_execution_venue, concentration
└── leadlag.py         # venue_return, lagged_correlation -- research only

tests/unit/crossvenue/
├── conftest.py
├── test_consensus.py
├── test_fragmentation.py
└── test_leadlag.py
```

**Structure Decision**: `leadlag.py` is deliberately absent from `__init__.py`.
The prohibition in PRD §17.2 — "do not convert correlation to a trading rule" —
cannot be verified by reading intent, so it becomes a structural fact: importing
it takes a fully qualified module path, and a test walks the signal, alerting
and stop packages asserting none contains that path ([[ADR-040]]). The same test
asserts those three packages still exist, so deleting them cannot turn the check
green.

## Approach

**Executable prices are supplied, not computed** ([[ADR-039]]). Fees, gas and
MEV margins are venue-specific operational inputs. An engine that assumed them
would bury those assumptions at every call site; taking them as arguments puts
them where the caller can see them.

**Mid-based basis refuses for an AMM** (PRD §18.14). The formula in §17.3 is
arithmetically well-defined for a pool and economically meaningless there, which
is exactly the shape of mistake that produces a plausible number. So it raises,
and `executable_basis_bps` at a caller-supplied notional is the answer instead —
with no default notional, because every venue costs the same at zero size.

**"Cannot fill" and "expensive" are different answers.** A venue that cannot
fill the notional is excluded from the ranking and named in the exclusion list,
rather than ranked last.

**Comparability comes from the registry.** Two quotes are comparable when their
representation keys resolve to one canonical asset — never when their tickers
match, which is the merge §18.13 forbids.

## Complexity Tracking

> No violations.
