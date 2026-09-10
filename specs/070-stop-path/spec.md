---
traces: [REQ-WP-032]
status: draft
---

# Feature Specification: The stop path as it was generated

**Feature Branch**: `wp-032-stop-path`

**Created**: 2026-09-10

**Status**: Draft

**Input**: REQ-WP-032 — Phase 7A's stop-path chart.

## Context

PRD §44A.33 lists fifteen things a position view must display, and then one
rule: `AS-SEEN-THEN` mode must show the stop path exactly as generated
live/replay, **not recompute a prettier historical trail**.

The list is a drawing. The rule is the requirement, and it is the one a view
breaks by doing the easy thing. Given a position and a price series, recomputing
the trail is less work than carrying the proposals, produces a smoother line,
and is wrong: it draws each stop using anchors confirmed after the instant it
draws them at. The result is a chart of a stop that could not have been placed —
Principle I's look-ahead, in the one place where it looks like polish.

The second thing worth stating: **a hold is not a gap.** [[ADR-032]] spent its
argument keeping six kinds of hold distinguishable in the model — held because
no anchor was knowable, held on a cooldown, held under a data-quality freeze,
held because moving would widen risk. A view that draws only movements collapses
all six back into one flat line, at the last step before a human reads it, and
the distinction is precisely what someone inspecting a stop decision came for.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The path is carried, not recomputed (Priority: P1)

**Acceptance Scenarios**:

1. **Given** a position with a recorded stop path, **When** the path is drawn, **Then** every level comes from a recorded proposal.
2. **Given** the same position and a later price series that would suggest a tighter trail, **When** the path is drawn, **Then** the drawn path is unchanged.
3. **Given** `AS_SEEN_THEN` and an instant, **When** the path is drawn, **Then** no proposal later than the instant appears.

---

### User Story 2 - A hold is shown as a hold (Priority: P1)

**Acceptance Scenarios**:

1. **Given** proposals that moved and proposals that held, **When** they are drawn, **Then** the two are distinguishable.
2. **Given** two holds with different reasons, **When** they are drawn, **Then** they are distinguishable from each other.
3. **Given** any proposal, **When** it is drawn, **Then** its anchor and its reason codes travel with it.
4. **Given** a refused proposal, **When** it is drawn, **Then** it is rendered as refused, not omitted.

---

### User Story 3 - The levels are four distinct things (Priority: P2)

**Acceptance Scenarios**:

1. **Given** a position, **When** its levels are read, **Then** entry, initial stop, hard stop and current adaptive stop are separate.
2. **Given** a position with no hard stop, **When** its levels are read, **Then** the hard stop is absent — not the initial stop, not zero.
3. **Given** an empty path, **When** excursion is read, **Then** it is unavailable with a reason rather than zero, while open risk still reads from the position's own accepted risk.

### Edge Cases

- **A path of holds only.** The stop never moved. The path is a flat line and every point on it says why it did not move — which is a different chart from an empty one.
- **A proposal whose anchor is absent.** A hold with no knowable anchor has none. Absent, never substituted with the previous anchor.
- **An instant before the position opened.** Nothing to draw; not an empty position at the entry price.
- **A position still open.** There is a current adaptive stop and no exit. The path ends at the last proposal, not at the right edge of the chart.
- **Reason codes the view does not recognise.** Carried through and shown, not dropped. A view that silently drops an unknown reason turns a new veto into no veto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The drawn path MUST be derived only from recorded proposals; the view MUST NOT be given a price series to recompute from.
- **FR-002**: In `AS_SEEN_THEN`, no proposal later than the instant MUST appear.
- **FR-003**: Proposals that moved and proposals that held MUST be distinguishable.
- **FR-004**: Holds MUST remain distinguishable from each other by their reasons.
- **FR-005**: A refused proposal MUST be rendered, not omitted.
- **FR-006**: Every proposal MUST carry its anchor and reason codes to the view.
- **FR-007**: Entry, initial stop, hard stop and current adaptive stop MUST be separate levels.
- **FR-008**: An absent hard stop MUST be absent.
- **FR-009**: Excursion figures MUST be unavailable, with a reason, when no path has been observed — never reported as zero. Risk figures MUST come from the position's own levels, which are knowable whether or not the policy ever ran.
- **FR-010**: Existing chart views MUST be unchanged.

### Key Entities

- **Stop path**: the ordered proposals a policy actually made, each with the instant it was made, what it decided, the anchor it used, and why.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Drawing the same position twice with different subsequent price data produces the same path.
- **SC-002**: A path filtered at an instant contains no proposal after it.
- **SC-003**: Given a path of holds only, every drawn point states a reason and the path is not empty.
- **SC-004**: A position with no hard stop reports no hard-stop level.
- **SC-005**: An empty path yields unavailable excursion figures naming why, and open risk still reads 1.0R from the accepted initial risk.
- **SC-006**: Every existing web test passes unchanged.

## Assumptions

- **The view is a pure decision, tested as one.** `lightweight-charts` cannot lay out a container under jsdom, so the decision — which levels, which markers, at which instants, with which labels — lives in a module the tests can reach, and the component attaches it. This is the split [[REQ-WP-027]] and [[REQ-WP-028]] already use.
- **FR-001 is enforced by the signature, not by discipline.** The module is never handed bars. A view that has no price series cannot recompute a trail from one, which turns the constitutional rule into a thing the type system holds rather than a thing a reviewer has to notice.
- **Nothing stores stop proposals yet.** [[REQ-WP-020]] built the engine; no table holds its output and no endpoint serves it, exactly as nothing writes derivative features. This specifies the view over the shape the engine already produces. Recording and serving the path is its own requirement, and the phase's third open deliverable is adjacent to it.
- **"Why moved / Why not tighter"** — §44A.33's click panel — groups reason codes the model already distinguishes. The grouping is this feature's; the codes are [[REQ-WP-020]]'s and are not re-derived.
- **Trail aggressiveness and data-health status** are listed fields with no producer. They are out of scope here and named in Open Questions rather than silently dropped.

## Open Questions

- **Trail aggressiveness** has no definition in §44A.33 beyond the phrase, and nothing computes it. Deferred.
- **Data-health status** exists as a freeze reason in the policy but not as a view-level status. Deferred.
