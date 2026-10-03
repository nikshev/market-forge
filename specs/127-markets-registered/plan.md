# Implementation Plan: The markets the stack ingests are listed, with the market type the venue's stream really is

**Branch**: `127-markets-registered` | **Date**: 2026-10-03 | **Spec**: [spec.md](./spec.md)

## Summary

Each ingest process registers the `(venue, symbol)` it ingests in the markets table at start-up, once,
with no trading rules, and with a market type that comes from the venue registry. Registration is
idempotent and soft: it never costs a bar. Nothing else about ingest, the table, the API or the page changes.

## What planning measured

**The writing code exists and is in the wrong layer.** `LakehouseRepository.add_market` (in `channelflow.api`)
writes the no-rules row; `ingest_main` must not import the API. The row is built inline there, so the plan
moves its construction to `tables/features.py` beside `market_row`, and `add_market` calls it: one
definition of "a market with no rules", used by both.

**The registry has no market type, and its connectors say two different things.** Binance's daemon
connects to `stream.binance.com:9443` (`websocket.binance_stream_url`), the **spot** stream; Bybit's to
`…/v5/public/linear` (perpetuals); OKX's URL names nothing, the instrument does: `BTC-USDT-SWAP` is a
perpetual and `BTC-USDT` would be spot. So a constant per venue is right for two venues and wrong for OKX
the day somebody configures a different instrument. The type is therefore a **function of the symbol** on
each registry entry, like `stream_builder`: binance and bybit return a constant, OKX reads the suffix and
**refuses** a form it does not recognise rather than guess.

**The live table is empty and the list route reads it whole.** `{"markets":[]}` today; five rows after.

**The overview page already renders what is needed** (`symbol` as a link to the chart, `venue · type`,
scores shown as absent), so no page code changes; one test pins the five-row shape.

**Concurrency.** Five daemons restart together after a deploy. `IcebergTable.append` is Iceberg's
retry-on-conflict ([[REQ-WP-039]]); the markets read keeps the latest row per key, so a duplicate row cannot
reach the list.

## Technical Context

**Language/Version**: Python 3.12, `mypy --strict`; the page unchanged (TypeScript 5.6, one added test)

**Storage**: the existing `markets` Iceberg table; schema unchanged

**Testing**: pytest (fast gate; real SQLite catalog), one integration test on the stack's PostgreSQL, vitest

## Constitution Check

| Principle | Result |
|---|---|
| VIII. Connectors share one interface | **Engaged and held.** The market type joins the registry that already holds each venue's URL, policy and subscription: one entry per venue, one place. |
| X. Thresholds are configuration | Not engaged: nothing numeric. |
| XII. Correctness precedes performance | **Engaged.** A false market type on the first screen is the correctness fault; a start-up read of a five-row table is not a performance concern. |
| XIV. Everything is traceable | Python and tests marked `REQ-WP-081`. |

No violation; Complexity Tracking is empty.

## Decisions, and what each rejected

**D1. The daemon registers its own market.** It is the one component configured with the venue and symbol.
Rejected: a separate registrar process (told the same list twice); the `worker` registering (it knows the
timeframes, not the venues); seeding the table by hand or by a migration (a list that goes stale the day a
symbol is added to compose).

**D2. The type is `market_type(symbol)` on the registry entry.** Rejected: a constant on the entry (wrong
for OKX the day the instrument changes); a mapping in the registration code (a second home for a venue's
facts); inferring from the URL at registration (OKX's URL says nothing).

**D3. A test ties the type to the endpoint.** For each venue, the endpoint the daemon really uses implies a
market type (`stream.binance.com` spot, `fstream.binance.com` perp, `/linear` perp, `/spot` spot, `-SWAP`
perp), and the registry's answer must agree. If Binance's URL changes to futures, the test fails until the type is reconsidered.

**D4. No trading rules.** Rejected: a start-up `exchangeInfo` call for Binance only — nothing reads the
fields, and it would be a new way for ingest to fail.

**D5. Soft failure, no retry loop.** Any exception while registering (including an unrecognised OKX
instrument) is one WARNING naming venue and symbol; ingest continues; the next start retries.
Rejected: failing ingest (the product is the bars, not the list); retrying in a loop (a stuck loop and a log flood).

**D6. Idempotence by reading first.** Read the markets table, skip when the key is present. Rejected: append
always and rely on the read's dedupe (one more row per restart, forever, in an append-only table).

## Tests (written first)

pytest, fast gate: the registry has a market type for every venue (SC-004), and agrees with each venue's
endpoint (D3); OKX refuses an unrecognised instrument form; `unruled_market_row` is what `add_market` writes
(the existing repository tests pass unchanged); registering writes one row and reads back with no
instrument; registering twice, and ten times, leaves one row for the key; a key held with trading rules is
recognised and not overwritten; five keys registered from five threads end with five rows; through `main`:
a failing registration logs one WARNING naming venue and symbol, then ingest runs, and an unrecognised
instrument does the same. vitest: the five-row response renders five links with their types. Integration:
the same five threads against the stack's PostgreSQL catalog.

## Project Structure

```text
src/channelflow/connectors/venue.py              # market_type on VenueConfig and the three entries
src/channelflow/tables/features.py               # unruled_market_row
src/channelflow/api/lakehouse_repository.py      # add_market uses it
src/channelflow/pipeline/market_registration.py  # register_market, register_softly
src/channelflow/pipeline/ingest_main.py          # calls it before ingesting
tests/unit/pipeline/test_market_registration.py  tests/unit/connectors/test_market_types.py
tests/integration/test_market_registration.py    apps/web/src/__tests__/marketsFiveRows.test.tsx
tests/mutations/market_registration.toml         docs/deployment.md
```

## Deployment

Recreate the five ingest services only (`--no-deps`): each loses up to fifteen buffered bars, the documented
trade, and the 24-hour measurement of [[REQ-WP-079]] concerns `worker` and `resample`, which are not touched.
