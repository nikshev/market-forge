# Phase 0 — Research

## 1. Which panes?

**Decision**: CVD, OFI (1m) and depth imbalance (10) — the three Phase 2 has
data for.

**Rationale**: PRD §27.3 lists nine. OI, funding, basis and liquidations are
Phase 3's own deliverable and the DEX pair is Phase 4's. Offering an empty pane
and calling it a feature puts a phase's unfinished work in front of a reader as
though it were finished.

**Where the list came from**: the PRD, not a preference. The design question was
nearly asked of the user and did not need to be — §27.3 answers it outright.

## 2. Gap or zero?

**Decision**: gap, and a real zero still drawn.

**Rationale**: the API returns a mapping per instant, and a mapping without the
key is silent. A flat line through the middle of a CVD pane says "no net delta",
which is a claim about the market rather than about the data. The two halves are
implemented and tested as a pair, because either alone is satisfiable by an
implementation that gets the other wrong.

## 3. Three empty-ish states, or one blank?

**Decision**: three — no points, no values for this feature, and a failed load.

**Rationale**: one blank for all three is what an implementation falls into. The
main chart already refuses it (`LoadState`, [[REQ-WP-009]]'s FR-016) and a new
pane showing one blank would quietly undo that. A reader who sees "no readings
of this feature" looks for the feature; one who sees "no points in this window"
looks at the window.

## 4. What the wiring found

Two `role="status"` elements on one page broke two existing tests that asked for
"the status". Their intent was about the overlay-restoration notice, and being
the only status on the page was what made them unambiguous. Both statuses are
now named, and the tests ask by name — which is what they meant and could not
say before.
