---
traces: [REQ-US-002]
status: draft
---

# Feature Specification: The alert's link restores the chart it was sent about

**Feature Branch**: `us-002-deep-link-overlays`

**Created**: 2026-09-09

**Input**: REQ-US-002 — "clicking the Telegram button opens the chart at exactly
the signal's timestamp; all overlays active at signal time are restored." PRD
§27.1's deep link and §27.2's overlay list.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Land on the moment the alert is about (Priority: P1)

The chart opens centred on the signal's own timestamp, not at the end of the
loaded history.

**Why this priority**: REQ-US-002 says "exactly the signal's timestamp". A view
that merely contains the instant somewhere leaves the reader to find it, and on
a 500-bar window they will find the wrong one.

**Acceptance Scenarios**:

1. **Given** a link carrying an instant, **When** the chart opens, **Then** the visible range is centred on the bar covering that instant.
2. **Given** an instant older than the loaded history, **When** the chart opens, **Then** the range is not centred on a bar that does not exist, and the whole history is shown instead.
3. **Given** a link with no instant, **When** the chart opens, **Then** the whole loaded history is shown.
4. **Given** an instant at the very edge of the history, **When** the chart opens, **Then** the range stays inside the data rather than extending past it.

---

### User Story 2 - See the layers that were on when the alert fired (Priority: P1)

The link carries which of PRD §27.2's overlays were active, and the chart draws
exactly those.

**Why this priority**: the second half of REQ-US-002. A chart that opens with a
different set of layers than the one the setup was judged on is showing a
different picture and saying nothing about the difference.

**Acceptance Scenarios**:

1. **Given** an alert declaring its active overlays, **When** its link is built, **Then** the link names them.
2. **Given** a link naming overlays, **When** the chart opens, **Then** exactly those layers are drawn.
3. **Given** an alert declaring no overlays, **When** its link is built, **Then** the link omits the parameter rather than naming a default set.
4. **Given** a link with no overlay parameter, **When** the chart opens, **Then** a declared default set is drawn and the page says the alert's own set was not restored.
5. **Given** a link naming an overlay nobody recognises, **When** the chart opens, **Then** none of the list is applied — the same "not restored" state as an absent parameter, said out loud.
6. **Given** one alert, **When** its link is built twice, **Then** the two links are identical.

---

### Edge Cases

- What happens when the overlay list is partly recognisable? The whole list is discarded. A restored subset is a chart that looks restored while silently missing whichever layers the reader most needed — the same reasoning [[ADR-020]] applies to a mangled channel mode.
- What happens when an overlay names a layer this chart cannot draw yet? It is a recognised name, so it applies; the layers this build draws are a subset of §27.2 and will grow. A name the PRD does not list is what gets refused.
- What happens when the same overlay appears twice in the link? It is drawn once. A duplicate is not an error worth discarding the link for.
- What happens when the alert is for a chart the reader cannot load? Unchanged from today: the load state says so, and there is no picture to restore anything onto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: An alert MUST be able to declare the overlays active when it fired, from PRD §27.2's list, and an unlisted name MUST be refused.
- **FR-002**: The deep link MUST name the declared overlays, in a stable order, and MUST omit the parameter when none are declared.
- **FR-003**: Two links built from one alert MUST be identical.
- **FR-004**: The chart MUST draw exactly the overlays the link names.
- **FR-005**: An absent overlay parameter MUST produce a declared default set, and the page MUST say the alert's set was not restored.
- **FR-006**: An overlay list containing any unrecognised name MUST be discarded whole, producing the same stated fallback.
- **FR-007**: A duplicate overlay name MUST NOT draw the layer twice.
- **FR-008**: The chart's visible range MUST be centred on the bar covering the link's instant.
- **FR-009**: An instant outside the loaded history MUST leave the range as the whole history rather than centring on nothing.
- **FR-010**: A range MUST NOT extend past the loaded data.

### Key Entities

- **Overlay**: one of §27.2's toggleable layers.
- **Restoration state**: whether the alert's own overlay set was applied, defaulted, or discarded.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A link built from an alert with overlays names them; one without omits the parameter.
- **SC-002**: The same alert produces the same link twice.
- **SC-003**: An unlisted overlay name is refused at the alert.
- **SC-004**: A link's overlays are exactly the layers drawn.
- **SC-005**: A missing or unrecognised list produces the default set and a stated notice.
- **SC-006**: The visible range is centred on the signal's bar, verified against a hand-computed index.
- **SC-007**: An out-of-range instant leaves the full history visible.

## Assumptions

- **The pipeline decides which overlays were active.** This feature carries that decision to the chart; it does not infer it from the alert's contents, which would be a guess presented as a restoration.
- **The chart draws a subset of §27.2 today** — candles, channel lines, zones, the marker and the volume profile. The overlay vocabulary is the PRD's full list, so a link written now stays valid as layers are added.
