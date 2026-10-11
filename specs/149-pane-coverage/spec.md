---
traces: [REQ-WP-097]
status: draft
---

# Feature Specification: Every lower pane the deployment can fill has data, and the rest say why

**Feature Branch**: `149-pane-coverage`

**Created**: 2026-10-11

**Status**: Draft

**Input**: [[REQ-WP-097]] -- owner's direction 2026-10-11 ("make all the data display"); PRD §27.3, §45 Phase 2 and 3. Depends on specs 145-148.

## Context

Four requirements build producers for the panes that read "no data". This one is the **acceptance of the whole, on the deployed stack**, so that "every pane has data" is a recorded measurement and not a belief. A green unit suite proved the six trade features and said nothing about the nine panes that were empty for a month.

### What is measured

For every market the deployment lists and every timeframe the page offers, each lower pane is in exactly one of three states: **has data** (a point in the loaded range), **absent for a stated, true reason** (a spot market has no perpetual consensus; a symbol with no liquidation in the range; a pane with no source such as the DEX), or -- the state this removes -- **absent because the producer is not deployed**.

### What this is not

Building any producer (specs 145-148), changing the page, or building DEX ingest.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One command prints the truth about the panes (Priority: P1)

An operator runs a script against the running API and reads, per market and timeframe, the state of every pane.

**Why this priority**: it is the acceptance; without it the claim is unchecked.

**Independent Test**: the script, run against a stub API in a unit test, classifies fixtures into the three states and fails on "no producer".

**Acceptance Scenarios**:

1. **Given** a stub API where one pane has points, **When** the script runs, **Then** it prints `data` for that pane.
2. **Given** a pane with no points and a known reason (a refusal reason from the venue-basis read, a spot market with no perpetual consensus), **When** it runs, **Then** it prints `absent: <reason>`.
3. **Given** a pane with no points and no reason, **When** it runs, **Then** it prints `NO PRODUCER` and exits non-zero.

---

### User Story 2 - The deployment is what the commits describe (Priority: P1)

**Independent Test**: the collector services are up and healthy; the worker image was built from a clean committed tree; the run is recorded in the outcome note.

**Acceptance Scenarios**:

1. **Given** the stack, **When** the services are listed, **Then** each collector is running, healthy and has been for the interval the note records.
2. **Given** the worker's image labels, **When** read, **Then** they name a committed revision and not a dirty tree.

---

### User Story 3 - The page is seen (Priority: P2)

**Independent Test**: a screenshot of a chart with the pane row, light and dark, kept under `docs/ui/` and looked at.

**Acceptance Scenarios**:

1. **Given** the deployed page, **When** a BTC chart is opened, **Then** the enabled panes are the ones the script reports as having data.

### Edge Cases

- A symbol that simply had no liquidation in the range is `absent: no event in range`, only if the collector's heartbeat covers the range (spec 146).
- A market added later: the script reads the markets list, never a hard-coded one.
- The API down: the script says so and exits with a distinct code, rather than printing an empty table.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A script in `tools/` reads `/api/v1/markets` and the timeframes, queries the feature series and the venue-basis read for each market and timeframe over a stated range, and prints the three-state table.
- **FR-002**: Classification is a pure function over the API's answers and is unit-tested without a network.
- **FR-003**: A pane with no points and no stated reason is `NO PRODUCER` and the script exits 1; an unreachable API exits 2.
- **FR-004**: Reasons come from the system's own answers (a refusal reason, the heartbeat, the DEX source list), never from a table of excuses in the script.
- **FR-005**: The recorded run, the service listing with health and ages, and the image revision are put in the outcome note.
- **FR-006**: Every new file carries a requirement trace.

### Key Entities

- **Pane state**: `data`, `absent` (with reason) or `no-producer`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The recorded run over every listed market and timeframe has zero `NO PRODUCER` cells.
- **SC-002**: The cells for the three BTC series at 1m, 5m, 15m and 1h are `data` for open interest, funding (z), basis, OFI, depth imbalance and, for the two perpetual venues, venue basis.
- **SC-003**: Every `absent` cell carries a reason taken from the system.
- **SC-004**: The screenshots show the same enabled panes as the table.

## Assumptions

- The producers of specs 145-148 have run long enough for the range checked to contain data; the note records how long.
- DEX panes are reported as `absent: no DEX source` unless a DEX requirement is delivered; that is a true reason.
