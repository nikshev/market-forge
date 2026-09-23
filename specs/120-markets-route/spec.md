---
traces: [REQ-WP-075]
status: draft
---

# Feature Specification: The markets route

**Feature Branch**: `120-markets-route`

**Created**: 2026-09-23

**Status**: Draft

**Input**: [[REQ-WP-075]] — PRD §27.1 (the routes) and §28.1 (`GET /api/v1/markets`).

## Context

§27.1 lists five routes; only `/chart/:venue/:symbol` is built. Every other
path — including `/markets` and `/` — renders the same two lines:
"ChannelFlow" and "Open a chart at /chart/&lt;venue&gt;/&lt;symbol&gt;", because
`parseDeepLink` returns `null` and `App` has no other branch.

The read behind the view already exists. §28.1's `GET /api/v1/markets` returns
one entry per market with its §43 rank, supports `venue`, `market_type`,
`quote`, `active` and `min_volume` filters, and already places an unscored
market after every scored one with nulls rather than a zero
([[REQ-US-001]], `rank_markets`).

**The PRD names no `/` route.** Serving this view at the root as well is this
deployment's decision, recorded here so a reader comparing §27.1 with the
running app finds the difference explained rather than inferred.

### What "current state" is allowed to mean

The list is the state: one row per market, carrying what §28.1 already returns
and §43 already scores. This feature introduces **no new aggregate, no new
endpoint and no number computed for the first time** — a summary that invented
its own figures would become a second source of truth for quantities the API
already publishes.

An unscored market must read as unscored. The API's own rule is that ranking it
at zero "would place it among the worst setups, saying it had been examined and
found weak"; a view that renders a null as `0.00` undoes that at the last step.

### There is no look-ahead in a list

The list is a set of current values, not a series. Nothing here reads a
timeframe's bars, and nothing is evaluated at an instant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The markets list (Priority: P1)

A reader opens `/markets` and sees the deployment's markets in the order the
API ranked them, with unscored ones plainly unscored.

**Why this priority**: this is the view §27.1 names, and every other story is
about reaching it or leaving it.

**Independent Test**: stub the API with a list in a known order, including one
unscored entry, and assert the row order and the unscored marking.

**Acceptance Scenarios**:

1. **Given** a markets read returning three markets, **When** the page renders,
   **Then** one row per market appears, in the order returned.
2. **Given** a market whose score fields are null, **Then** the row reads as
   unscored — not `0`, not `0.00`, not an empty cell.
3. **Given** a scored market, **Then** its rank score is shown with its value.

---

### User Story 2 - Choosing a market and a timeframe (Priority: P1)

A reader picks a timeframe, clicks a market, and lands on the chart's deep link
at that timeframe. A pasted link with the same values produces the same page.

**Why this priority**: a list that cannot open a chart is a dead end, and
§27.1's whole shape is "overview → detail".

**Independent Test**: render the view, choose a timeframe, activate a market's
link, and compare the destination with the deep link built from the same
`venue`, `symbol` and `tf`.

**Acceptance Scenarios**:

1. **Given** the list, **When** the reader activates a market at the default
   timeframe, **Then** the destination is
   `/chart/<venue>/<symbol>?tf=<default>`.
2. **Given** the reader chose `4h`, **When** a market is activated, **Then**
   the destination is `/chart/<venue>/<symbol>?tf=4h`, byte for byte a link a
   human could have pasted.
3. **Given** that destination is opened fresh, **Then** the chart shows the
   same timeframe — the frame already delivered by [[REQ-WP-074]].

---

### User Story 3 - The root path (Priority: P2)

A reader who types the host's address with no path sees the markets view, not
the placeholder.

**Why this priority**: `/` is where a reader arrives first; a placeholder there
is the product looking unfinished. It is P2 because `/markets` alone already
delivers the view.

**Independent Test**: render with pathname `/` and assert the same rows appear.

**Acceptance Scenarios**:

1. **Given** pathname `/`, **Then** the markets view renders.
2. **Given** pathname `/markets`, **Then** the same view renders.
3. **Given** any other unknown path, **Then** the existing placeholder remains,
   naming where a chart can be opened — the fallback is not replaced by a
   redirect that hides the mistake.

---

### User Story 4 - The offered timeframes are the deployment's (Priority: P2)

The timeframe control on this view offers what `GET /api/v1/timeframes`
reports, exactly as the chart's does.

**Why this priority**: a second list here would be the disagreement
[[REQ-WP-073]]'s FR-002 and [[REQ-WP-074]] exist to prevent.

**Independent Test**: serve an unseen set, render, and find its tokens among
the options.

**Acceptance Scenarios**:

1. **Given** a deployment offering `1m, 5m, 15m, 1h`, **Then** the view offers
   exactly those, and a market activated after choosing `1h` links to `?tf=1h`.
2. **Given** the offered set cannot be read, **Then** the view states that
   failure rather than offering no timeframes silently — the load is a failure,
   not an empty configuration.

---

### Edge Cases

- **No markets.** The read succeeds with an empty list: the view says there are
  none — a fact about the deployment — never that the load failed.
- **A failed markets read.** Stated with its detail (FR-016's rule), never drawn
  as an empty list, which would read as "no markets".
- **A failed offered-set read.** Stated; the market rows may still render, but
  the timeframe control does not pretend to have options. (The destination's
  timeframe matters, so a link built without a chosen timeframe uses the
  default.)
- **A market with no `venue`/`symbol`.** The API requires both as non-empty
  strings, so the view does not re-validate them; a row is a link to what the
  API said.
- **Special characters in venue or symbol.** The destination encodes them, so
  the link is still openable.
- **A market activated twice quickly.** Navigation is a plain link; the browser
  owns it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `/markets` MUST render one row per entry of `GET /api/v1/markets`,
  in the order the API returned, with no client-side re-sorting.
- **FR-002**: A market whose score is null MUST read as unscored — visually
  distinct from a zero score.
- **FR-003**: The root path `/` MUST render the same view. Every other unknown
  path MUST keep the existing placeholder.
- **FR-004**: Each market MUST offer navigation to
  `/chart/<venue>/<symbol>?tf=<chosen>`, equal to the deep link constructed from
  the same values.
- **FR-005**: The offered timeframes MUST come from `GET /api/v1/timeframes`;
  the view MUST NOT carry its own list. The initial choice is the documented
  default, defined once.
- **FR-006**: A failed markets read MUST be stated with its detail; an empty
  list MUST read as an absence of markets. The two MUST NOT be conflated.
- **FR-007**: The `/chart/:venue/:symbol` route MUST behave exactly as
  [[REQ-WP-074]] left it.

### Key Entities

- **Market row**: what §28.1 returns — `venue`, `symbol`, `market_type`, and
  three nullable scores. Displayed as received; not recomputed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero client-side re-sorting: the rendered order equals the API's
  order for a fixture whose two orders differ (e.g. ranked ascending).
- **SC-002**: An unscored market's row contains no numeric score rendering; a
  scored one shows its value.
- **SC-003**: The destination of a chosen market at a chosen timeframe is
  string-identical to the deep link a human would write for the same values,
  proven by comparing the generated href with the expected path and query.
- **SC-004**: Zero timeframe tokens are hard-coded in the view; an unseen set
  renders as options, measured as in [[REQ-WP-074]]'s SC-003.
- **SC-005**: On the running deployment, `/markets` lists the markets
  `GET /api/v1/markets` returns, and activating one reaches the chart.

## Assumptions

- The filters §28.1 supports are not surfaced in this view. The requirement
  asks for the list; a filter UI is a separate decision and is not smuggled in.
- Each row links to the chart at one selected timeframe rather than offering a
  per-row timeframe menu. One control for the view matches the chart's own
  control and keeps the row a single link.
- Navigation is a full page load (an ordinary link). The chart is a separate
  route and already parses its link at mount ([[REQ-WP-074]]); a client-side
  router is not needed for two routes.
- Scoring semantics — what `rank_score` means, how it is computed — belong to
  [[REQ-US-001]] and §43. This view only presents them.
