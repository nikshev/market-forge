---
traces: [REQ-WP-074]
status: draft
---

# Feature Specification: The timeframe is chosen on the chart

**Feature Branch**: `119-chart-timeframe-control`

**Created**: 2026-09-23

**Status**: Draft

**Input**: [[REQ-WP-074]] — PRD §27.1 (the deep link), §27.2/§27.3 (a chart of
selectable controls), §5.1 (the timeframes), §28.2 (`GET /api/v1/bars` takes
`timeframe`).

## Context

The chart parses `tf` from the link and then asks for fifteen minutes
regardless. `parseDeepLink` returns `DeepLink.timeframe`
(`apps/web/src/deepLink.ts`), the heading prints it, and every request is built
from `const timeframeNs = 15 * MINUTE_NS` (`apps/web/src/App.tsx:62`). Measured
on the running stack, 2026-09-17: the one-minute series returned 133 bars and
the fifteen-minute request returned `{"bars":[]}`, so the chart rendered
`empty` — a correct report of a question asked at the wrong timeframe.

Two things changed underneath since. [[REQ-WP-073]] now produces every
configured timeframe, so the series exist and the API returns them at
`timeframe_ns` values other than fifteen minutes. And §27.2's "Toggle layers"
and §27.3's "Selectable panes" are already implemented, so a chart with controls
is the established shape; a timeframe row is one more.

**§27 does not name a timeframe selector.** This feature is derived from §5.1's
set, §28.2's parameter, §27.1's link and §27.2/§27.3's controls — the same kind
of derivation `docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`
records for other criteria. The reference shape is investing.com's chart
toolbar: a row of timeframe buttons above the chart. This specification settles
behaviour; styling and component library are deliberately not settled.

### The link is the initial value, not the alternative

`tf` must keep working. §27.1 is the link **every alert this system sends**
carries, and an alert that opened a chart at the wrong timeframe would
misrepresent the signal it was about. So the link names the timeframe the chart
**opens** at; the control changes it afterwards; a link with no `tf` opens at the
documented default.

### A control that changes the screen and not the link is the other half

`apps/web/src/App.tsx` contains no `history.replaceState` or `pushState` at all.
`modeFromQuery` reads `as_seen_then` to initialise the mode, `ChannelModeControl`
changes the mode, and the URL still describes the state the reader left — a
copied link then reproduces something other than what was on screen. The
timeframe control must not repeat this, and fixing the mode control's half is in
scope here because the mechanism is one mechanism.

### The offered set comes from the deployment

The timeframes a deployment produces are configuration ([[REQ-WP-073]]'s
FR-002), and §28 lists no endpoint carrying them. A list written into the
frontend would be a second source that can disagree with the first, and the
disagreement would look like a chart with no data. So this feature settles the
API surface: a read that reports the offered set, and a chart that offers
exactly what it reports.

**`1m` is offered even though `CHANNELFLOW_TIMEFRAMES` does not name it.** §5.1
lists `1m` among the Phase 1 timeframes, and the ingest daemon produces it
always; the configuration names what *resampling* builds. The offered set is
therefore the source timeframe plus the configured targets.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choosing a timeframe re-reads everything at it (Priority: P1)

A reader opens `BTCUSDT`, presses `1h`, and the candles, channel, feature series
and extrema are re-read at one hour.

**Why this priority**: this is the defect. Every other story is about the link,
the address or the refusal.

**Independent Test**: open a chart, click a second timeframe, and inspect the
requests that reached the network — bars, channel, features and extrema must
each carry the chosen `timeframe_ns`. For at least two values would pass; the
test asserts two, because one constant passes for one value.

**Acceptance Scenarios**:

1. **Given** a chart open at `15m`, **When** the reader presses `1h`, **Then**
   the bars, channel, features and extrema requests all carry one hour's
   `timeframe_ns`, and the chart redraws from their answers.
2. **Given** a chart open at `1h`, **When** the reader presses `5m`, **Then**
   the same happens at five minutes.
3. **Given** the reader changes timeframe twice quickly, **Then** the last
   choice is what the chart shows — a slower earlier response does not overwrite
   a later one.

---

### User Story 2 - The link still opens at the timeframe it names (Priority: P1)

An alert's link carries `tf=4h`; opening it shows four-hour candles. A link with
no `tf` opens at the documented default. A link naming a timeframe the
deployment does not produce is refused **visibly**, naming it.

**Why this priority**: the alert path is the reason the chart exists, and a
silent fallback would show one timeframe's candles under another's name.

**Independent Test**: render the chart with a `tf` query and assert the first
request's `timeframe_ns`; repeat for a second value and for no value at all.

**Acceptance Scenarios**:

1. **Given** a link carrying `tf=4h`, **When** the page loads, **Then** the
   first bars request carries four hours.
2. **Given** a link carrying no `tf`, **When** the page loads, **Then** the
   first bars request carries the default, and the default is defined in one
   place rather than repeated per request.
3. **Given** a link carrying `tf=7m` (a token this system has no series for) or
   `tf=1M` (a calendar period), **When** the page loads, **Then** the page says
   which timeframe could not be honoured and issues no request at a substituted
   timeframe.
4. **Given** a link carrying a valid token the deployment is not configured to
   produce, **When** the page loads, **Then** the refusal names that token and
   lists what the deployment does offer.

---

### User Story 3 - The address keeps up with the controls (Priority: P2)

The reader presses `30m` and then CURRENT REFIT; copying the address bar
reproduces exactly the view on screen, at that timeframe and in that mode.

**Why this priority**: without it the link is a one-way input. An alert link
that opens correctly but cannot be shared back is half a link.

**Independent Test**: change the controls, read `window.location.search`, open
the same path and search fresh, and compare the first request it makes with the
screen's current one.

**Acceptance Scenarios**:

1. **Given** a chart open at `15m`, **When** the reader presses `30m`, **Then**
   the address carries `tf=30m`.
2. **Given** a chart in AS-SEEN-THEN, **When** the reader switches to CURRENT
   REFIT, **Then** the address describes the refit, and switching back leaves an
   address that opens AS-SEEN-THEN.
3. **Given** an address already carrying `at=`, `signal=` or overlay
   parameters, **When** the timeframe changes, **Then** those parameters are
   still there — the timeframe control does not drop the rest of the link.
4. **Given** a link copied after a change, **When** it is opened fresh,
   **Then** the first request it makes matches the request the screen made.

---

### User Story 4 - The control offers what the deployment has (Priority: P2)

The chart's timeframe options are what the API reports for this deployment. A
timeframe added to configuration appears without a frontend change.

**Why this priority**: it is [[REQ-WP-073]]'s FR-002 carried to the frontend. A
hard-coded list here would recreate the defect that requirement removed.

**Independent Test**: serve a set the frontend has never seen, render the chart,
and find those tokens among the offered buttons.

**Acceptance Scenarios**:

1. **Given** a deployment offering `1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w`, **Then**
   the control offers exactly those, in duration order.
2. **Given** a set that includes a timeframe no test fixture previously used,
   **Then** it appears in the control with no frontend source change.
3. **Given** the offered set cannot be read, **Then** the page states that
   failure rather than drawing an empty control that looks like a shape with no
   data (FR-016).

---

### Edge Cases

- **The offered set has not arrived yet.** No bars request is issued before the
  offered set is known, so no request is made at a timeframe the deployment may
  not have.
- **A timeframe with no bars.** The chart reads `empty`, not `failed` — the
  distinction FR-016 draws and the code already honours. An empty series is a
  quiet market, not a failure.
- **A failed bars request.** The chart reads `failed` with its detail and is
  never drawn as an empty chart.
- **`tf` repeated in the query** (`?tf=1h&tf=5m`). The first wins, as
  `URLSearchParams.get` already does; the behaviour is stated because it is
  observable.
- **The link names a timeframe and the offered set arrives rejecting it.** The
  refusal appears once the set is known; no request is issued before that.
- **The default timeframe is missing from the deployment's set.** The default is
  refused like any other unhonourable token, naming it, rather than silently
  choosing a neighbour.
- **Changing timeframe while a signal is in the link.** `signal` stays in the
  address; whether it is re-read is [[REQ-WP-009]]'s behaviour, unchanged here.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The chart MUST offer a timeframe control whose options are the
  deployment's offered set, in ascending duration order, with the in-force
  timeframe marked as selected.
- **FR-002**: The system MUST expose a read that reports the offered set — each
  timeframe's token and its duration in nanoseconds — computed from the same
  configuration the producer reads, plus the source timeframe. The set MUST NOT
  be carried by the frontend as a constant.
- **FR-003**: Choosing a timeframe MUST re-read bars, channel, feature series
  and extrema at that timeframe, and the redraw MUST use those answers.
- **FR-004**: Every request the chart issues MUST carry the timeframe in force.
  A request carrying any other value, or a constant, MUST fail the tests that
  assert the parameters that reached the network.
- **FR-005**: The link's `tf` MUST be the timeframe the chart opens at. A link
  with no `tf` MUST open at a single documented default defined in one place.
- **FR-006**: A `tf` that is unparseable, a calendar period, or outside the
  offered set MUST be refused visibly, naming the token, with no request issued
  at a substituted timeframe.
- **FR-007**: Changing the timeframe MUST update the address so that opening the
  resulting link anew reproduces the timeframe in force.
- **FR-008**: Changing the channel mode MUST update the address so that opening
  the resulting link anew reproduces the mode in force. Absence of the parameter
  MUST mean the default mode, as [[ADR-020]] already requires.
- **FR-009**: Address updates MUST preserve the other link parameters —
  `at`, `signal`, `chain`, `pool` and the overlay parameters.
- **FR-010**: When the offered set cannot be read, the page MUST state the
  failure, never render a control with no options as though that were an answer.
- **FR-011**: A timeframe whose series is empty MUST read as `empty`, and a
  failed read MUST read as `failed` — the two MUST NOT be conflated in either
  direction.
- **FR-012**: A response older than the current selection MUST NOT overwrite a
  newer one; the timeframe in force is the last one chosen.
- **FR-013**: The heading the reader sees MUST name the timeframe in force —
  the displayed value and the requested value MUST be one value, not two.

### Key Entities

- **Offered set**: the timeframes this deployment can serve, as reported by
  FR-002 — the source timeframe plus the resampler's configured targets.
- **In-force timeframe**: the token the chart is currently showing, initialised
  from the link and changed by the control.
- **Default timeframe**: the token a link with no `tf` opens at, defined once.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Choosing a timeframe re-reads all four series at it, proven by the
  parameters that reached the network for at least two values — so a constant
  cannot pass.
- **SC-002**: A link copied after one control change opens a fresh page whose
  first request matches the request the screen last made — for the timeframe and
  for the mode.
- **SC-003**: Zero timeframe tokens are hard-coded in the frontend as an offered
  set; a set the frontend has never seen renders as offered buttons, measured by
  the diff needed to serve one: no frontend source change.
- **SC-004**: An unhonourable `tf` produces a visible refusal naming it, and zero
  requests carry a substituted timeframe.
- **SC-005**: On the running deployment, `/chart/binance/BTCUSDT?tf=1h` shows
  candles at one hour — the claim [[REQ-WP-073]]'s quickstart explicitly could
  not make and deferred to this feature.

## Assumptions

- The offered set is read once, at page open. A configuration change requires a
  deployment restart, so a live subscription would observe nothing.
- `1m` is always offered: the ingest daemon produces it, and §5.1 names it.
- The default timeframe is `15m`, kept from `parseDeepLink`'s current behaviour
  and written in one place. It is expected to be in the offered set; if a
  deployment configures it away, FR-006 refuses it like any other token.
- Presentation — control styling, button versus menu, component library — is
  not settled by this specification, deliberately ([[REQ-WP-074]]'s Reference).
- The existing `LoadState` vocabulary (`ok`, `empty`, `failed`) is the one this
  feature extends to the offered set's own read; no second failure vocabulary is
  introduced.
- The API's own configuration read follows the repository's no-defaults rule;
  the deployment passes the variable to both the resampler and the API from one
  value.
