# Research: candidates off by default, "no data" panes

Each decision: what was chosen, why, what else was looked at. The code was read, not assumed.

## R1. Where "has data" comes from

**Decision**: the series the page already loads, through `paneSeries`.
**Why**: `GET /features/timeseries` returns points whose `values` map holds every feature the API has at that
instant (`FeaturePointOut.values: dict[str, float]`), and `App.tsx` already requests it for the visible range.
`paneSeries(...).state === "ok"` is "some point carries a number under this key".
**Alternatives**: `/features/snapshot` (one instant, one more request); a registry endpoint listing built
features (does not exist, would answer "ever", not "in this view"); a constant list in the page (drifts).

## R2. How candidates reach the chart

**Decision**: `extremumMarkers({..., includeCandidates})`, called by `Chart` with the page's switch.
**Why**: that function already withholds candidates not yet observed at the instant in AS-SEEN-THEN and those
replaced by a shown confirmation. Hiding them there keeps one definition of "visible at t".
**Default**: `includeCandidates` defaults to `true` in the pure function so its 13 existing call sites keep their
meaning; `Chart` passes the page's switch explicitly and a test pins that.
**Alternatives**: filtering `extrema.candidates` in `App` before it reaches `Chart` (works, but the pure
function stops being the thing a test pins, and `Chart`'s effect deps would not see the intent).

## R3. Whether the link carries the switch

**Decision**: no. `OVERLAYS` mirrors `channelflow.alerting.Overlay` and an existing test rejects names outside
§27.2; a link with an unknown name is discarded whole ([[REQ-US-002]]).
**Alternatives**: add a name to both sides (changes a PRD-derived vocabulary for a convenience); a separate
query parameter (a second link state with its own restoration rules and notices, for a default of "off").

## R4. "Loading" is not "no data"

**Decision**: `pointsLoaded` in `App`, false from the start of a load until the series answer (ok or failed).
**Why**: `points` is `[]` before the first answer, which `paneSeries` reports as `empty`. FR-006 forbids
presenting that as an absence. `available = null` means "not known".

## R5. The accessible name of a "no data" pane

**Decision**: a disabled MUI `ToggleButton` with the label and a "no data" text, no `aria-label`.
**Why**: the name stays what the reader sees ("CVD no data"), the control is `disabled` (announced as
unavailable) and a pane with data is byte-for-byte the old button. A tooltip on a disabled button needs a
wrapper element and is not read by assistive technology.
