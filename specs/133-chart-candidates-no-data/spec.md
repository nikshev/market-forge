---
traces: [REQ-WP-084]
status: draft
---

# Feature Specification: The chart hides candidate extrema until asked; a pane with no data says so

**Feature Branch**: `133-chart-candidates-no-data`

**Created**: 2026-10-04

**Status**: Draft

**Input**: [[REQ-WP-084]] — PRD §27.2, §27.3; the owner's direction of 2026-10-04.

## Context

Looking at the Material UI chart the owner asked two things: what the small arrows are, and why the buttons
under the chart do nothing.

**The arrows** are extrema. A *confirmed* extremum is a filled-colour arrow; a *candidate* is a grey arrow with
a "?", which the detector may still invalidate. Candidates are many and sit on the price, so the first view of a
chart is mostly question marks. Confirmed extrema are the structure; candidates are work in progress, and a
reader should ask to see them.

**The buttons** are §27.3's nine panes. A pane is a button for a feature the page names; whether the feature
has any stored series is not known until it is pressed, and for most of them today it never will be. The page
already says so *after* the press ("No cvd readings among these points"). It should say so before.

### Facts read from the code, which decide the design

- The page already loads **one** feature series for the visible range (`/features/timeseries`), and each point
  carries a `values` map of **every** feature the API has for that instant. So "which panes have data" is
  already in the page's hands: a pane has data when some loaded point has a number under its feature's name.
  No new API call is needed, and a feature producer that is added later makes its pane live with no change here.
- `paneSeries` already distinguishes three states, deliberately: `empty` (no points at all), `unavailable`
  (points, none carrying this feature) and `ok`. This feature reuses that function as the one definition of
  "has data" rather than writing a second.
- The deep link's `overlays` list is **§27.2's vocabulary and nothing else**: an existing test rejects a name
  outside it, and a list with an unknown name is discarded whole ([[REQ-US-002]]). Candidate extrema are not
  one of §27.2's twelve layers, so the switch cannot be a link layer without breaking that rule. It is a view
  option of the page.
- `extremumMarkers` draws confirmed and candidate marks in one call, so the candidate marks are filtered out
  *before* drawing rather than hidden afterwards.

### What "no data" means, and what it must not mean

"No data" is the state of a pane whose series is `empty` or `unavailable` **for the loaded view**. It is not a
failure (a failed load is a failure and keeps its own message, [[REQ-WP-009]] FR-016), and it is not "not yet
loaded" (while the series is loading the row does not claim anything). And it is not a claim about the market:
"no data in this view" says nothing about a feature that has readings outside the visible range.

### What this is not

Not a feature producer: CVD, OFI and the rest still have none, and most panes will honestly read "no data"
until separate work gives them one. Not a change to what a candidate or a confirmation is, to the API, or to
the deep link.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Candidates are off until asked (Priority: P1)

**Independent Test**: render the chart with confirmed and candidate extrema and read the marks handed to the
chart; press the switch and read them again.

**Acceptance Scenarios**:

1. **Given** extrema with confirmed and candidate entries, **When** the chart opens, **Then** only the confirmed
   marks are drawn.
2. **When** the "Candidate extrema" switch is turned on, **Then** the candidate marks are drawn as well,
   exactly as the API returned them; turned off, they go again.
3. **Then** the switch is a labelled control whose pressed state is exposed (`aria-pressed`), and it is off on
   every fresh page load.
4. **Given** a deep link with or without an `overlays` list, **Then** the list is read exactly as before and the
   switch is off; a link naming a candidates layer is still unreadable, because that is not a §27.2 name.
5. **Given** no candidates in the response, **Then** the switch is still shown (it is a view option, not a
   report) and turning it on draws nothing extra.
6. **Given** AS-SEEN-THEN, **Then** candidates that the mode would already withhold ([[REQ-NRT-A]] family: nothing
   later than the instant) are still withheld when the switch is on: the switch widens the view, it never
   looks ahead.

---

### User Story 2 - A pane with no data says so before it is pressed (Priority: P1)

**Independent Test**: render the pane row with series in each of the three states and read the controls.

**Acceptance Scenarios**:

1. **Given** a loaded series in which only some features carry values, **Then** a pane whose feature carries a
   value in some point is a button exactly as today (role, name, `aria-pressed`), and every other pane reads
   "no data" in place of an active button.
2. **Then** a "no data" pane cannot be pressed and is announced as unavailable (`disabled`, not only styled);
   its name still says which pane it is, so the reader knows what is missing, not only that something is.
3. **Given** a series with no points at all, **Then** every pane reads "no data".
4. **Given** a failed feature load, **Then** the failure message is shown as today and no pane is labelled
   "no data" (a failure is not an absence).
5. **Given** the series is still loading, **Then** no pane is labelled "no data".
6. **Given** a feature with a reading in one point and gaps elsewhere, **Then** it has data: gaps inside a
   series are the existing silence, not a "no data" pane.
7. **Given** a pane that had data and a later load (another timeframe, another market) has none, **Then** it
   becomes "no data" and, if it was selected, the selection moves as in Story 3.

---

### User Story 3 - The page does not open on a pane with nothing in it (Priority: P2)

**Acceptance Scenarios**:

1. **Given** the first pane (CVD) has no data and another pane does, **When** the page loads, **Then** the
   first pane **with data** is selected.
2. **Given** a pane the reader chose and which still has data, **Then** it stays chosen across a reload of the
   same view: the page never overrides a valid choice.
3. **Given** no pane has data, **Then** none is selected and the pane region says "No pane has data for this
   view", in the role the pane notes already use (`status`).

---

### User Story 4 - Looked at (Priority: P2)

**Acceptance Scenarios**:

1. **Then** screenshots of the chart with candidates off (default) and on, and of the pane row with some panes
   "no data", light and dark, are taken from the running build and kept under `docs/ui/`, and each is looked at.

### Edge Cases

- A feature with a value of `0`: that is data. Only an absent key is a gap (`paneSeries` already says so).
- Two points at one instant: unchanged; `paneSeries` keeps the last.
- A feature name in the series that is not one of the nine panes: ignored; it gets no button.
- Candidates that arrive after the switch was turned on (a refetch): still drawn while it is on.
- The switch while the extrema request failed: nothing to draw, and the existing failure behaviour is unchanged.
- Phone width: the pane row scrolls inside itself as it does now, with disabled buttons included.
- Reduced motion: nothing animates.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The chart MUST draw no candidate extremum while the "Candidate extrema" switch is off, and MUST
  draw the candidates the API returned, unchanged, while it is on. Confirmed extrema MUST be drawn in both states.
- **FR-002**: The switch MUST be off on every page load and MUST NOT be carried by, read from or written to the
  deep link; the link's `overlays` list MUST be read exactly as before.
- **FR-003**: The switch MUST expose its state to assistive technology and MUST NOT change which candidates are
  available at the selected instant (no look-ahead; Principle I).
- **FR-004**: A pane MUST read "no data" and be disabled when `paneSeries` for its feature is `empty` or
  `unavailable` for the loaded view; any other pane MUST be exactly the button it is today.
- **FR-005**: The decision of FR-004 MUST come from the loaded series through `paneSeries`, with no list of
  feature names added to the page for it and no new API call.
- **FR-006**: A failed or in-flight feature load MUST NOT label any pane "no data".
- **FR-007**: A "no data" pane MUST keep its name in the control row and MUST be unpressable.
- **FR-008**: When the selected pane has no data the page MUST select the first pane that has data; when none
  has, it MUST select none and say so in a `status` region. A valid choice MUST NOT be overridden.
- **FR-009**: Every role and accessible name the existing web tests find for a pane that has data MUST be unchanged.
- **FR-010**: Screenshots of candidates off and on, and of the pane row with "no data" panes, light and dark,
  MUST be kept under `docs/ui/`.

### Key Entities

- **Candidate switch**: a boolean view option of the chart page; default off; not persisted.
- **Pane availability**: for each of the nine panes, whether the loaded series carries its feature (`ok`) or not
  (`empty` / `unavailable`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With three confirmed and four candidate extrema, the chart is handed three marks by default and
  seven with the switch on, and the three are the same three.
- **SC-002**: With a series that carries only `ofi_1m`, exactly one pane is a button and eight read "no data";
  with an empty series nine do; with a failed load none does.
- **SC-003**: The existing web tests pass with only the edits each outcome note lists.
- **SC-004**: The screenshots exist and were looked at; what looking showed is recorded.

## Assumptions

- "Has data" is for the view the page loaded, not for all time; the wording on screen says "no data" and the
  note says "for this view". A pane with readings only outside the visible range is "no data" until the reader
  moves there. This is stated, not hidden.
- The switch's label is "Candidate extrema" and the pane note is "no data"; wording may be adjusted in the plan
  without changing the contract above.
- Producing CVD, OFI and the other features is out of scope and is separate work the owner has asked for.
- Remembering the switch across reloads (local storage) is out of scope: the safe default on every open is off.
