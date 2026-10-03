---
id: REQ-WP-081
title: "The markets the stack ingests are listed, with the market type the venue's stream really is"
type: work-package
prd_ref: "§27.1, §28.1, §6.2"
prd_lines: "4388-4400, 4461-4475, 405-420"
phase: null
status: implemented
depends_on: [REQ-WP-021, REQ-WP-075, REQ-WP-076]
tags: [markets, overview, ingest]
hard_gated: false
---

## Requirement

PRD §27.1 makes `/markets` the overview route and §28.1 serves it: one entry per market. The overview
exists ([[REQ-WP-075]]) and the endpoint exists. On 2026-10-03, with five ingest services delivering
bars, `GET /api/v1/markets` answered `{"markets":[]}` — and so the first screen of the product is empty.

The cause is not a bug in either. The list is read from the `markets` table, and **no running process
writes to it**. The code to write one exists (`LakehouseRepository.add_market`, `market_row`) and a
Binance normalizer for the trading rules exists ([[REQ-WP-021]]); nothing calls them in the stack. The
markets table was filled only by tests.

This requirement makes each ingest process register the market it ingests.

### What a registered market is

A row for `(venue, symbol)` with its **market type** and no trading rules. Rules (tick, step, minimum
notional) are not registered: nothing uses them yet ([[REQ-WP-021]] says so), only Binance has a
normalizer, and a network call at start-up to fill a field nobody reads would be a new way for ingest to
fail. A row without rules is a state the table and the API already represent (`instrument` is absent).

### The market type has to be true

The Binance daemon connects to `wss://stream.binance.com:9443`, which is Binance's **spot** stream; the
Bybit daemon to `…/v5/public/linear` and the OKX daemon to a `-SWAP` instrument, which are perpetuals.
PRD §26.1's example alert says "Binance Perp"; this deployment's Binance data is not. Registering all
three as `perp` would be the convenient answer and a false one, shown on the first screen. So the market
type is a property of the **venue registry** — the one place that already holds each venue's URL and
policy — and is not written anywhere else.

### Registering must never cost a bar

Ingest is the product; the overview is not. A failure to register — the catalog unreachable at start,
a commit conflict that does not resolve — is a WARNING that names the venue and symbol, and ingest
continues. The registration is retried the next time the process starts, and not in a loop.

## Acceptance

- **Five rows.** After the stack starts, `GET /api/v1/markets` lists one entry for every `(venue, symbol)`
  an ingest service ingests today — binance BTCUSDT, ETHUSDT, SOLUSDT; bybit BTCUSDT; okx BTC-USDT-SWAP —
  recorded with the date, from the running stack and not from a test.
- **The type is the venue's.** Each entry carries the market type from the registry: binance `spot`,
  bybit and okx `perp`. A test fails if a registry venue has none, or if the Binance stream URL changes
  without the type being reconsidered.
- **Registering twice adds nothing.** Starting the same daemon again leaves one row for its key (a real
  table, read back), however many times it starts.
- **Registering fails softly.** With an unreachable catalog, the daemon logs one WARNING naming the venue
  and the symbol and goes on to ingest (a test through `main`, not through the helper alone).
- **No rules are invented.** A registered market reads back with no instrument, and the API says so
  (nulls), as it does for any market without rules.
- **The overview shows them.** The page's list renders one row per entry, each a link to its chart at the
  chosen timeframe, from the real API response (a test with that response's shape).

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-127-markets-registered]]
- **Tests:**
    - `tests/unit/connectors/test_market_types.py::test_binance_is_spot_because_its_stream_is_the_spot_stream`
    - `tests/unit/connectors/test_market_types.py::test_bybit_is_perp_because_its_endpoint_is_the_linear_one`
    - `tests/unit/connectors/test_market_types.py::test_every_venue_in_the_registry_names_a_market_type`
    - `tests/unit/connectors/test_market_types.py::test_okx_reads_its_instrument_not_its_venue[BTC-USDT-SWAP-perp]`
    - `tests/unit/connectors/test_market_types.py::test_okx_reads_its_instrument_not_its_venue[BTC-USDT-spot]`
    - `tests/unit/connectors/test_market_types.py::test_okx_reads_its_instrument_not_its_venue[ETH-USDT-SWAP-perp]`
    - `tests/unit/connectors/test_market_types.py::test_okx_refuses_an_instrument_it_does_not_recognise_rather_than_guess[BTC-USDT-240329]`
    - `tests/unit/connectors/test_market_types.py::test_okx_refuses_an_instrument_it_does_not_recognise_rather_than_guess[BTC-USDT-SWAP-X]`
    - `tests/unit/connectors/test_market_types.py::test_okx_refuses_an_instrument_it_does_not_recognise_rather_than_guess[BTCUSDT]`
    - `tests/unit/connectors/test_market_types.py::test_okx_refuses_an_instrument_it_does_not_recognise_rather_than_guess[]`
    - `tests/unit/connectors/test_market_types.py::test_the_endpoint_table_would_notice_a_futures_binance`
    - `tests/unit/lakehouse/test_concurrent_create.py::test_the_writer_that_lost_the_race_returns_its_own_snapshot`
    - `tests/unit/lakehouse/test_concurrent_create.py::test_writers_racing_to_create_the_same_table_all_land`
    - `tests/unit/pipeline/test_market_registration.py::test_a_failing_registration_is_one_warning_naming_venue_and_symbol_and_ingest_runs`
    - `tests/unit/pipeline/test_market_registration.py::test_a_key_held_with_trading_rules_is_recognised_and_not_overwritten`
    - `tests/unit/pipeline/test_market_registration.py::test_an_instrument_okx_does_not_recognise_is_a_warning_and_ingest_runs`
    - `tests/unit/pipeline/test_market_registration.py::test_an_unreachable_catalog_is_the_same_soft_warning`
    - `tests/unit/pipeline/test_market_registration.py::test_five_keys_registered_at_once_end_with_five_rows`
    - `tests/unit/pipeline/test_market_registration.py::test_register_softly_reports_what_it_did_and_never_raises`
    - `tests/unit/pipeline/test_market_registration.py::test_registering_twice_adds_nothing`
    - `tests/unit/pipeline/test_market_registration.py::test_registering_writes_one_row_that_reads_back_with_no_instrument`
    - `tests/unit/pipeline/test_market_registration.py::test_ten_starts_leave_one_row_for_the_key`
    - `tests/unit/pipeline/test_market_registration.py::test_the_row_carries_the_type_the_registry_gives_that_venue[binance-BTCUSDT-spot]`
    - `tests/unit/pipeline/test_market_registration.py::test_the_row_carries_the_type_the_registry_gives_that_venue[bybit-BTCUSDT-perp]`
    - `tests/unit/pipeline/test_market_registration.py::test_the_row_carries_the_type_the_registry_gives_that_venue[okx-BTC-USDT-SWAP-perp]`
    - `tests/unit/pipeline/test_market_registration.py::test_the_row_carries_the_type_the_registry_gives_that_venue[okx-BTC-USDT-spot]`
    - `tests/unit/pipeline/test_market_registration.py::test_the_row_is_exactly_what_the_repository_writes_for_a_market_without_rules`
    - `tests/unit/pipeline/test_market_registration.py::test_two_symbols_of_one_venue_are_both_registered`
- **Code:**
    - `src/channelflow/api/lakehouse_repository.py`
    - `src/channelflow/connectors/venue.py`
    - `src/channelflow/lakehouse/iceberg.py`
    - `src/channelflow/pipeline/ingest_main.py`
    - `src/channelflow/tables/features.py`
- **Outcomes:** [[OUT-2026-10-03-implement-markets-registered]], [[OUT-2026-10-03-plan-markets-registered]], [[OUT-2026-10-03-spec-markets-registered]], [[OUT-2026-10-03-tasks-markets-registered]]
<!-- trace:end -->

## Notes

Human territory. Never machine-rewritten.

Out of scope: trading rules for Bybit and OKX; scores and ranking (an unscored market sorts after a
scored one and carries nulls, as [[REQ-WP-075]] already says); DEX markets; removing a market that is
no longer ingested.

### 2026-10-03: what building it found

Five daemons started together on an empty catalog and **four lost a race to create the table**
(`TableAlreadyExistsError` out of `IcebergTable.append`), which this requirement's own soft-failure rule
would have turned into four warnings and four unlisted markets after every deploy. Found by the thread
test, fixed in `append` (a writer that loses the race uses the table that won), and tested without threads
by forcing the interleaving. Live: five markets listed on 2026-10-03 at 17:06 UTC, binance spot and bybit
and okx perp, and two restarts of one daemon left the list at five.
