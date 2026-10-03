---
traces: [REQ-WP-081]
status: draft
---

# Feature Specification: The markets the stack ingests are listed, with the market type the venue's stream really is

**Feature Branch**: `127-markets-registered`

**Created**: 2026-10-03

**Status**: Draft

**Input**: [[REQ-WP-081]] — PRD §27.1 (`/markets` is the overview route), §28.1 (`GET /api/v1/markets`),
§6.2 (one ingest service per venue).

## Context

With five ingest services delivering bars, `GET /api/v1/markets` answered `{"markets":[]}` on
2026-10-03. The overview page ([[REQ-WP-075]]) reads exactly that, so the first screen of the product
says "No markets are configured on this deployment" while five are running.

Nothing is broken in the endpoint or the page. The list comes from the `markets` table, and **no running
process writes to it**. The writing code exists (`LakehouseRepository.add_market`, `market_row`), a
Binance normalizer for trading rules exists ([[REQ-WP-021]]), and the table was filled only by tests.

### What each running daemon already knows

Every ingest process is configured with one venue and one symbol. It is the one component that knows
what is being ingested, so it is the one that can say so. A separate process would have to be told the
same list a second time, and a list in two places is the kind of thing this repository has found
disagreeing with itself ([[REQ-WP-078]]'s two registries).

### The market type has to be true

| venue | what the daemon connects to | market type |
|---|---|---|
| binance | `wss://stream.binance.com:9443` — Binance's **spot** stream | `spot` |
| bybit | `wss://stream.bybit.com/v5/public/linear` — linear perpetuals | `perp` |
| okx | a `…-SWAP` instrument on the v5 public socket | `perp` |

PRD §26.1's example alert reads "Binance Perp". This deployment's Binance data is not perpetual.
Registering all three as `perp` would be the convenient answer, and a false one, on the first screen. The
type is therefore a property of the **venue registry** — where each venue's URL and policy already live —
and is written nowhere else.

### What is deliberately not registered

Trading rules (tick, step, minimum notional). Nothing uses them yet ([[REQ-WP-021]]'s own note), only
Binance has a normalizer, and a network call at start-up to fill fields nobody reads would be a new way
for ingest to fail. A row without rules is a state the table and the API already represent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The overview lists what the stack ingests (Priority: P1)

**Why this priority**: it is the whole point, and the first screen of the product.

**Independent Test**: start the stack; read `/api/v1/markets` and open the overview.

**Acceptance Scenarios**:

1. **Given** the five ingest services running, **When** `/api/v1/markets` is read, **Then** it lists
   binance BTCUSDT, ETHUSDT, SOLUSDT, bybit BTCUSDT and okx BTC-USDT-SWAP, one entry each.
2. **Given** that response, **When** the overview renders it, **Then** each entry is a row linking to its
   chart at the chosen timeframe, showing its venue and market type, with its scores shown as absent.

---

### User Story 2 - The market type is the venue's (Priority: P1)

**Independent Test**: read the registry and the rows.

**Acceptance Scenarios**:

1. **Given** the registry, **Then** every venue in it names a market type, and binance's is `spot`,
   bybit's and okx's `perp`.
2. **Given** the Binance stream URL, **When** it changes to a futures endpoint, **Then** a test fails
   until the market type is reconsidered.

---

### User Story 3 - Registering is idempotent and never costs a bar (Priority: P1)

**Independent Test**: register twice against a real table; register with the write failing.

**Acceptance Scenarios**:

1. **Given** a daemon that has registered its market, **When** it starts again, **Then** the table still
   holds one row for its key, however many times.
2. **Given** a failing registration, **When** the daemon starts, **Then** one WARNING names the venue and
   the symbol and ingest goes on.
3. **Given** five daemons starting at once on an empty table, **Then** each key ends with one row.

---

### User Story 4 - No rules are invented (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a registered market, **When** it is read back, **Then** it has no instrument, and the API
   says so with nulls, as for any market without rules.

### Edge Cases

- A symbol registered under two cases (`btcusdt`, `BTCUSDT`): ingest already refuses a lower-case
  Binance or Bybit symbol, so one instrument has one key.
- A market that was registered and is no longer ingested stays listed: removing it is out of scope.
- The `markets` table holds rows from an older run with trading rules: they are not overwritten, and a
  registered key is recognised whatever else its row holds.
- Two daemons racing to register the same key: a duplicate row is possible between them, and the read
  already keeps the latest row per key, so it is harmless to the list; the table is not made to refuse it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each ingest process MUST register the `(venue, symbol)` it ingests in the markets table
  before it begins ingesting, unless that key is already present.
- **FR-002**: The registered row MUST carry the market type of the venue's registry entry and no trading
  rules.
- **FR-003**: Every venue in the registry MUST name a market type, and the type MUST NOT be written
  anywhere but the registry.
- **FR-004**: Binance's market type MUST be `spot` while its ingest stream is the spot stream, and a test
  MUST fail when the stream URL and the type disagree.
- **FR-005**: Registering a key that is present MUST add nothing.
- **FR-006**: A failure to register MUST be a WARNING naming the venue and the symbol and MUST NOT stop
  ingest, and MUST NOT be retried in a loop.
- **FR-007**: The overview MUST show one row per market the API lists, linking to its chart.

### Key Entities

- **Market**: a `(venue, symbol)` with a market type, and optionally trading rules.
- **Venue registry**: the one place that holds a venue's URL, policy, subscription and now market type.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the running stack, `/api/v1/markets` lists exactly five entries (today: zero), recorded
  with the date.
- **SC-002**: Starting a daemon ten times leaves one row for its key.
- **SC-003**: With registration failing, the number of bars an ingest process writes is unchanged.
- **SC-004**: 0 venues in the registry lack a market type.

## Assumptions

- Each ingest process ingests one symbol ([[REQ-WP-076]]); registration is per process.
- The markets table and its schema ([[REQ-WP-021]]) are unchanged.
- The overview page's rendering is correct as it stands; this changes what it is given.
- The markets list is small (five), so reading it whole at start-up is cheap.
