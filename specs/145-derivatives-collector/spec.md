---
traces: [REQ-WP-093]
status: draft
---

# Feature Specification: The derivatives panes are fed by a collector

**Feature Branch**: `145-derivatives-collector`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-093]] -- owner's direction 2026-10-11 ("make all the data display"); PRD §10.4, §16.1-16.3, §27.3. Principle I (no look-ahead), II (event time and receive time never conflated), [[REQ-BIAS-005]] (no using a funding settlement before it is known), [[ADR-026]] (no fallback values), [[ADR-070]].

## Context

The page's lower row has a pane for open interest, one for funding (z) and one for basis. All three read "no data".

### Facts measured on 2026-10-11, not assumed

1. **The features and the maths exist; the data does not.** `open_interest_usd`, `funding_z` and `basis_bps` are registered (`derivatives/registry_entries.py`), the functions that compute them are tested (`derivatives/openinterest.py`, `derivatives/funding.py`), and each connector has a `derivatives_state` normalizer. **No process calls a normalizer**, no table stores a `DerivativesState`, and the worker's feature step writes the six trade-derived features only (it does not iterate the registry).
2. **The sources answer from this host**, anonymously: Binance USD-M `premiumIndex`, `fundingRate` history and `futures/data/openInterestHist` (which carries `sumOpenInterestValue`, the open interest in USD as the venue reports it); Bybit linear `tickers` (`openInterestValue`, `indexPrice`, `markPrice`, `fundingRate`, `nextFundingTime`, `fundingIntervalHour`) and `funding/history`; OKX `open-interest` (`oiUsd`), `funding-rate` (with `prevFundingTime`, `settFundingRate`), `funding-rate-history`, `mark-price` and the index ticker. The connector module comment that the futures websocket streams are "unreachable from this network" is no longer true; this spec uses REST regardless.
3. **Binance's `openInterest` endpoint reports base units only.** `oi_series` skips base-only states on purpose: "multiplying by a price we chose would invent a figure the venue did not report". The USD figure therefore comes from the history endpoint, whose newest bucket is 5 minutes wide.
4. **`funding_z` needs 24 settled rates and a fresh settlement.** A venue settles every 8 hours (some symbols every 4), so 24 rates is 8 days of waiting. And `settled_funding` refuses unless the most recent settlement is within the staleness bound, whose default is 5 minutes -- so with the default, `funding_z` would exist for five minutes in eight hours.
5. **The deployment's series**: Binance BTC, ETH and SOL are **spot** markets; Bybit BTC and OKX BTC are perpetuals. The derivatives data of a venue belongs to its perpetual.
6. **The API needs no change for the panes to light up.** `GET /features/timeseries` returns every `feature_name` stored for the series at the requested timeframe, and the page enables a pane when a point carries its feature.

### What this is not

Liquidations ([[REQ-WP-094]]), the order book ([[REQ-WP-095]]), long/short ratios (§16.5 "optional when reliable"), cross-venue funding dispersion, and any change to the API or the web app.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The three panes show their series (Priority: P1)

Someone opens the Binance, Bybit or OKX BTC chart at any timeframe, selects Open interest, Funding (z) or Basis (bps), and sees a line.

**Why this priority**: it is the owner's request, and these three need only public REST data.

**Independent Test**: after the collector has run and the worker has completed one pass, the features endpoint for each of the three BTC series carries the three feature names at the viewed timeframe, and the panes are enabled.

**Acceptance Scenarios**:

1. **Given** a collector that has polled for a while, **When** the worker finishes a pass, **Then** every bar of a series after the first poll carries `open_interest_usd` and `basis_bps`.
2. **Given** the one-time funding history, **When** the worker finishes a pass, **Then** `funding_z` is present for bars after the 24th settlement.
3. **Given** the Binance spot series, **When** it is queried, **Then** it carries its venue's perpetual's values (see FR-012) and the registration says so.

---

### User Story 2 - A feature at time t uses only what was knowable at t (Priority: P1)

**Why this priority**: Principle I; this is the derivatives family's characteristic leak.

**Independent Test**: a value computed at a bar's close does not change when states with later event times are appended; funding uses only settled rates.

**Acceptance Scenarios**:

1. **Given** a stored fixture, **When** later states are appended, **Then** every feature at the earlier bar's close is identical.
2. **Given** a state whose funding interval has not closed at the bar's close, **When** `funding_z` is computed, **Then** that state's rate is not in the series.

---

### User Story 3 - A dead source is not shown as a live one (Priority: P1)

**Why this priority**: a poll that failed leaves the last figure in place, and a feature that repeats it reports a stale number as now.

**Independent Test**: with the collector stopped, bars after the staleness bound carry no row and the pane says "no data"; a failing client stores nothing.

**Acceptance Scenarios**:

1. **Given** a poll that fails, **When** the next cycle runs, **Then** nothing is stored for the failed poll and the previous state is not stored again.
2. **Given** a collector down for longer than the bound, **When** the worker runs, **Then** bars in the gap carry no open-interest or basis row.

---

### User Story 4 - The deployment runs it and shows its health (Priority: P2)

**Independent Test**: the compose services start, report healthy, and expose the age of the newest stored state.

**Acceptance Scenarios**:

1. **Given** the stack, **When** the collector services are started, **Then** each reaches healthy and exposes `context_last_state_age_seconds` per venue.
2. **Given** a collector that cannot reach its venue, **When** the health is read, **Then** it says so and is not healthy.

---

### User Story 5 - Funding history is loaded once, idempotently (Priority: P2)

**Independent Test**: running the history load twice stores each settlement once; rows are tagged as history.

**Acceptance Scenarios**:

1. **Given** an empty table, **When** the history is loaded, **Then** settlements appear with event time equal to the settlement time and a `history` source tag.
2. **Given** a loaded table, **When** it is loaded again, **Then** no row is added.

### Edge Cases

- **A venue changes a symbol's funding interval** (Binance publishes it per symbol): settlement times, not an assumed 8 hours, define the series; the staleness bound for settlement is read from the venue's reported interval plus a margin.
- **A rate limit (HTTP 429) or an IP ban** on a public endpoint: the poll backs off for the stated interval and stores nothing; it never retries in a tight loop.
- **A venue omits a field** (for example Bybit's `basis`, empty): the state has that field absent, never zero.
- **A clock step** or a state whose venue timestamp is in the future of the receive time: refused with a reason, stored in no table.
- **Many polled states per settlement**: the library's `settled_funding` does not collapse them, so the writer never gives it polled states; it gives it the history rows only (FR-005), one per settlement.
- **A constant funding series** (a floor for a day): `funding_z` is absent, per ADR-026, not zero.
- **Open interest from a venue reports base only**: not converted; absent.
- **The collector restarts**: no duplicate state for the same venue time (identity below), and the history load is a no-op.
- **Two series share a perpetual** (none today): each is given the same values; not an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A collector service, one process per venue, polls the venue's public derivatives endpoints on a fixed cadence (default 60 seconds) for each configured symbol and stores one `DerivativesState` per successful poll (§10.4: mark, index, funding rate, next funding time, open interest base and USD, basis).
- **FR-002**: Open interest in USD is the figure the venue reports. A venue that reports base units only for an endpoint does not have it converted.
- **FR-003**: `event_time` is the venue's own timestamp and `ingest_time` is when the collector received it, stored apart (Principle II). A state's identity is (venue, symbol, event time, source tag); a repeat is not stored twice.
- **FR-004**: A failed, rate-limited or unparseable poll stores nothing, is logged with its reason, increments a failure counter, and is retried only on the next cycle (after a backoff on a rate limit).
- **FR-005**: Settled funding comes from each venue's public history endpoint: rows carry the settlement time as event time and `next_funding_time` equal to it, and are tagged `history`. It is loaded at start (so `funding_z` has its 24 settlements at once) **and refreshed on a stated cadence** (default hourly) so each new settlement enters as it happens; both are idempotent. **`funding_z` reads only these rows**: a polled state carries the venue's current, still-revisable estimate for an interval in progress, and many polled states share one settlement time, so feeding them to a 24-observation window would fill it with one interval's estimates and call that 24 settlements.
- **FR-006**: A table `derivatives_state` stores the rows append-only, prices as decimals, with the source tag, and is covered by the maintenance service's compaction and expiry.
- **FR-007**: The worker, for every series and every timeframe with bars, writes `open_interest_usd`, `funding_z` and `basis_bps` to `feature_snapshots` at each bar's close, using the existing library functions and their refusals; the worker is the only writer of that table.
- **FR-008**: A value at a bar's close uses only states with event time at or before that close, and only settled funding rates (Principle I, [[REQ-BIAS-005]]).
- **FR-009**: Where the library refuses (stale, too few observations, constant series) or no state exists, no row is written for that feature and bar. Zero is never written for absence.
- **FR-010**: The staleness bound is explicit per feature: a few poll intervals for polled values; for funding, one funding interval plus a stated margin applied to the settlement. The values are named constants with their reason beside them.
- **FR-011**: The worker's watermark for these features is per series and feature, advances only over bars whose close is at or before the newest stored state's event time, so a bar is never skipped because its data had not arrived yet.
- **FR-012**: For a spot series, the derivatives are the same venue's perpetual of the same pair; the association is declared in one place (configuration the collector and the writer share) and stated in the feature registrations and `docs/deployment.md`. `basis_bps` is the perpetual's mark against the venue's index price.
- **FR-013**: The collector exposes health (the age of its newest stored state, consecutive failures) in the service's healthcheck and as Prometheus metrics; a collector that has stored nothing for longer than its bound is unhealthy.
- **FR-014**: Compose services for the three venues start with the stack; they hold no secrets; they are added without recreating any existing container.
- **FR-015**: The six trade-derived features keep their values and count.
- **FR-016**: Every new file carries a requirement trace (Principle XIV).

### Key Entities

- **DerivativesState** (§10.4): venue, symbol, event time, mark, index, funding rate, next funding time, open interest base and USD, basis; plus source tag (`poll` or `history`) and ingest time.
- **Series association**: (venue, symbol) of a market to the (venue, perpetual symbol) its derivatives come from.
- **Context feature row**: (at_ns = bar close, venue, symbol, timeframe, feature name, value).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the running stack, 24 hours after the collectors start, the features endpoint for Binance, Bybit and OKX BTC at the 1m, 5m, 15m and 1h timeframes returns `open_interest_usd`, `funding_z` and `basis_bps` for at least 95% of bars after the first poll (and for funding_z, after the 24th settlement, which the history makes immediate), and the three panes are enabled in the page.
- **SC-002**: A bar's three values are identical before and after appending states with later event times, across the whole fixture (zero differences).
- **SC-003**: With a collector stopped for longer than its bound, no bar inside the gap carries open interest or basis.
- **SC-004**: Running the history load twice stores each settlement exactly once.
- **SC-005**: The six existing features' stored rows are unchanged by the new pass (row counts and values equal before and after on the live lakehouse copy).
- **SC-006**: The collectors' combined CPU on the host stays under 5% of one core, measured, and no existing container is recreated by their start.

## Assumptions

- Public REST endpoints of the three venues are available without keys and stay within their documented limits at three calls a minute per symbol; the cadence is configurable.
- Binance's open interest USD at 5-minute resolution is the best the venue publishes for USD; the bound for it is therefore longer than for the others and is stated.
- The Binance series' derivatives from the same venue's perpetual are an acceptable reading of "open interest of this market" for a spot instrument, provided it is stated (FR-012).
- The history load seeds `funding_z` from rates that were public at their settlement; it is not a back-fill of data the system could not have had.
- Retention of the raw table follows the maintenance service's defaults.
