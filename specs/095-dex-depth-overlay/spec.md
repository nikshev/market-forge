---
traces: [REQ-WP-054]
status: draft
---

# Feature Specification: The DEX depth curve reaches the screen with its refusals intact

**Feature Branch**: `wp-054-dex-depth-overlay`

**Created**: 2026-09-12

**Status**: Draft

**Input**: REQ-WP-054 — PRD §27.2's "DEX liquidity bands".

## Context

§27.2 lists "DEX liquidity bands" among the chart's toggle layers, and the
toggle's name has been in the overlay vocabulary since [[REQ-US-002]] with no
layer behind it. Until [[REQ-WP-053]] there was nothing for one to read.

**The thing most likely to be lost on the path from table to pixel is
[[ADR-036]]'s refusal.** A band whose `reachable` is false describes exhausting
the known liquidity rather than reaching the target: the band was never reached,
and the notional is what ran out. Four boundaries lie between the stored row and
the drawn shape, and each is a chance to drop the flag — turning "this pool is
too thin to move 100 bps" into "100 bps costs this much here", which is a
cheaper-looking market than exists, drawn in the same ink as a real one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A band that declined to answer still says so (Priority: P1)

**Acceptance Scenarios**:

1. **Given** an unreached band, **When** it is served, **Then** it is marked unreached.
2. **Given** the same band, **When** it reaches the overlay, **Then** it is drawn differently from a reached one.
3. **Given** the same band, **When** the overlay is built, **Then** it is present rather than omitted.
4. **Given** an unreached band, **When** read, **Then** it says how far the book went.

---

### User Story 2 - The overlay reads as of the chart's instant (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a request without an instant, **When** made, **Then** it is refused.
2. **Given** a curve computed later, **When** asked for as of earlier, **Then** it is not returned.
3. **Given** several curves, **When** asked for, **Then** the newest at or before the instant is returned, whole.
4. **Given** the same question, **When** asked of either repository, **Then** the answers agree.

---

### User Story 3 - A failure is not an empty pool (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a failed load, **When** the overlay is built, **Then** it says so and draws nothing.
2. **Given** a pool with no curve, **When** the overlay is built, **Then** it says so differently.
3. **Given** a drawn overlay, **When** built, **Then** it carries no notice.

### Edge Cases

- **A nanosecond timestamp.** Larger than a JavaScript number can hold exactly.
- **A price with more digits than `float64`.** Crosses as an exact string.
- **A curve older than the cursor.** Drawn, with its own time reported so staleness is visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The endpoint MUST require an instant and MUST NOT default it.
- **FR-002**: It MUST return the newest curve at or before that instant, whole.
- **FR-003**: `reachable`, `reached_bps` and the reason MUST survive every boundary.
- **FR-004**: An unreached band MUST be present and marked, never omitted.
- **FR-005**: Money MUST cross the wire as exact strings.
- **FR-006**: Times MUST cross the wire as exact strings and be held as `bigint` in the client.
- **FR-007**: The overlay MUST distinguish a failed load from a pool with no curve.
- **FR-008**: The overlay MUST report the curve's own time, not the requested one.
- **FR-009**: Both repository implementations MUST agree about "as of".

### Key Entities

- **Depth band**: one side, one basis-point target, and whether it was reached.
- **Depth overlay**: what the chart draws, or why it draws nothing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An unreached band is distinguishable at the API and in the overlay.
- **SC-002**: A request without an instant is refused.
- **SC-003**: The two repositories agree at five instants.
- **SC-004**: A price `float64` cannot hold survives.
- **SC-005**: No test opens a socket.

## Assumptions

- **§27.3's "DEX active liquidity" pane is separate.** A lower pane reading a
  different primitive; bundling them would make both harder to review.
- **The drawing is the library's problem.** As `volumeProfile.ts` says: jsdom has
  no layout engine for a component test to see a shape through, so the decision
  about what to draw lives in a tested module and the rendering does not.

## Open Questions

- **Every other `_ns` field in the web app is a `number`.** A nanosecond epoch
  timestamp is around 1.7e18 against a safe maximum of 9.0e15, so each quantises
  to the nearest 256 nanoseconds. Measured. Fixing them all is a change across
  the whole app; this field is exact because it is new.
