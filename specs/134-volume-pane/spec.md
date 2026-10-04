---
traces: [REQ-WP-085]
status: draft
---

# Feature Specification: The lower panes include volume, drawn from the bars the page already loads

**Feature Branch**: `134-volume-pane`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-085]] — PRD §27.3; the owner's direction of 2026-10-04.

## Context

PRD §27.3 lists nine selectable lower panes and the first is **volume**. The page has nine panes and none is
volume: `depth_imbalance_10`, which §27.3 does not list, stands where it should be, and the comment above the
list says all nine of §27.3 are present. On 2026-10-04 the owner saw a row of buttons with nothing behind them
and said the data should already be there, "especially volume".

For volume it is. Every bar the API returns carries `volume_base`, and the chart page already loads the bars
(`BarOut.volume_base`, a decimal string). Volume needs no feature producer, no new feed and no API change.

### Facts read from the code, which decide the design

- `PANES` (`panes.ts`) is a list of **registered features**, and `tests/unit/features/test_pane_features.py`
  parses it and checks that every entry names one the registry knows. Volume is not a feature, so it must not be
  an entry of `PANES`: that would break an invariant that exists for a reason (a pane naming a feature nobody
  records shows "no readings" forever). Volume is a separate, bar-sourced pane, listed first in the row.
- `paneSeries(points, feature)` reads the feature series. Volume needs the same shape of answer (`ok` /
  `empty`, a note, points) from the bars, so a sibling `volumeSeries(bars)` returns a `PaneSeries`.
- [[REQ-WP-084]] decides availability from the loaded series and treats "not known" as `null`. Volume's
  availability is known as soon as the bars are, and does not depend on the feature series: a failed feature
  load must not take volume away.
- The chart draws candles at the bar's `close_time_ns` (`series.ts`); a pane is a small SVG with its own time
  scale and is not axis-locked to the chart. Volume uses the bar's `open_time_ns` as its time, the instant
  the bar *starts* (not the moment its volume became known, which is its close; the chart's candles use the
  close), and says nothing more about alignment than the other panes do.

### Volume is a property of the bar

A bar that is not final (`is_final` false) is still forming; its volume will change. The chart already refuses
to treat such a bar as finished, so the volume pane draws **final bars only**. A final bar in which nothing
traded has volume `0`, which is data (the bar exists and was quiet), not a gap.

### What this is not

Not a new API field, not a feature, not a quote-currency volume (`volume_base` is what bars carry), not a
change to the other panes' sources, and not the removal of `depth_imbalance_10`, which stays (whether to keep a
pane §27.3 does not list is for the owner to decide, not for this change to do by side effect).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Volume is the first pane (Priority: P1)

**Independent Test**: render the pane row with bars and read the first button and the drawing.

**Acceptance Scenarios**:

1. **Given** loaded bars, **Then** the pane row starts with a button named "Volume", and the other panes keep
   their labels, order and behaviour after it.
2. **Given** final bars with volumes, **When** Volume is selected, **Then** the pane draws one value per final
   bar, equal to that bar's `volume_base`, at that bar's time, as vertical bars (a volume is an amount per bar,
   not a line through them).
3. **Given** a final bar with volume `0`, **Then** it is drawn at zero, not skipped.
4. **Given** a bar that is not final, **Then** it contributes no volume point.
5. **Given** a `volume_base` such as `"12345.678901234"`, **Then** the drawn value is that number, not a
   two-decimal rounding of it.

---

### User Story 2 - It follows the availability rules of REQ-WP-084 (Priority: P1)

**Acceptance Scenarios**:

1. **Given** no bars, **Then** Volume reads "no data" and is disabled, like any pane with nothing behind it.
2. **Given** bars and a feature series that has not answered or has failed, **Then** Volume is a live button and
   draws; the feature failure message does not hide it and no pane claims "no data" while it is unknown.
3. **Given** bars and a feature series with no data, **Then** Volume is the only live pane and the page opens
   on it (no "No pane has data" message).
4. **Given** both bars and feature data, **Then** a reader's earlier valid choice stays; with none made, Volume,
   the first in the row, is selected.

---

### User Story 3 - The wrong claim is corrected (Priority: P2)

**Acceptance Scenarios**:

1. **Then** the comment above the pane list stops saying all nine of §27.3 are present, names the §27.3 panes,
   says which have data today (volume) and which have none yet, and says `depth_imbalance_10` is a pane this
   deployment added beyond the PRD's list.

---

### User Story 4 - Looked at (Priority: P2)

**Acceptance Scenarios**:

1. **Then** a screenshot of the chart with the Volume pane drawn on the **live** stack (real bars, no stub),
   light and dark, is kept under `docs/ui/` and looked at.

### Edge Cases

- No bars at all (the bar load succeeded and returned none): Volume is "no data" at once, even though the page never goes on to load the feature series.
- A series of one final bar: one value, drawn (a single bar has a width, not a division by zero).
- All volumes equal: drawn at one height, not collapsed to nothing.
- A `volume_base` that is not a number (an API fault): that bar is skipped, not drawn as zero.
- Bars with a gap between them: drawn at their own times; the pane makes no claim that they were adjacent
  ([[REQ-WP-086]] is about marking gaps).
- Very large and very small volumes: scaled to the pane's height, no overflow.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pane row MUST list Volume first, with the label "Volume"; every other pane keeps its label, order and behaviour.
- **FR-002**: `PANES` MUST remain a list of registered features; volume MUST be a separate bar-sourced pane.
- **FR-003**: The Volume pane MUST draw one value per final bar, equal to that bar's `volume_base`, at its time; a bar of volume `0` MUST be drawn at zero and a non-final bar MUST contribute nothing.
- **FR-004**: A `volume_base` MUST be parsed without losing the value the API sent; a value that is not a finite number MUST be skipped, not drawn as zero.
- **FR-005**: Volume MUST be "no data" (disabled) as soon as the bars have loaded and none is final, and MUST NOT depend on the feature series: a failed or in-flight feature load leaves it live. Before the bars have loaded, Volume says nothing (it is not "no data"); "the bars have loaded" is its own fact, not the feature series' (`barsLoaded`).
- **FR-006**: The page MUST open on the first pane with data, which with bars present is Volume, and MUST NOT override a reader's valid choice.
- **FR-007**: The comment above the pane list MUST be true.
- **FR-008**: A screenshot of the live Volume pane, light and dark, MUST be kept under `docs/ui/`.

### Key Entities

- **Bar-sourced pane**: a pane whose values come from the loaded bars rather than the feature series (volume).
- **Volume series**: `PaneSeries` over the final bars: `{ at_ns: open_time_ns, value: Number(volume_base) }`.

## Success Criteria *(mandatory)*

- **SC-001**: With 12 final bars and one non-final, the pane holds 12 values, equal to the bars' volumes.
- **SC-002**: With bars and an empty feature series, exactly one pane (Volume) is live and it is selected; with a failed feature series Volume is still live.
- **SC-003**: The existing 377 web tests pass with only the edits the outcome note lists, and `test_pane_features.py` is unchanged.
- **SC-004**: The live screenshots exist and were looked at.

## Assumptions

- `volume_base` is the volume the PRD means by "volume" at this stage; a quote-currency volume is not on the bar and is not invented.
- The pane keeps the other panes' fixed width and its own time scale.
