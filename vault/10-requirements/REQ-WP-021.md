---
id: REQ-WP-021
title: An instrument's trading rules are ingested, stored and served
type: work-package
prd_ref: "Phase 1 — CEX channel MVP; §29.B; §41 rule 9"
prd_lines: "6702-6702"
phase: 1
status: specified
depends_on: [REQ-WP-003, REQ-STORE-002, REQ-API-001]
tags: []
---

## Requirement

PRD §45's Phase 1 deliverables list, one line:

    - basic market metadata;

That is all the PRD says. No section elaborates it, none of Phase 1's five
acceptance criteria depends on it, and it is the last of Phase 1's twelve
deliverables with nothing behind it — which is why [[REQ-PHASE-1]] cannot leave
`planned`.

So "basic" is derived rather than quoted, from what the rest of this system
would need to know before it could claim a trade was realisable:

- **the price increment** (`tick_size`). A backtest that fills at a price the
  venue cannot quote has filled at a price that does not exist.
- **the quantity increment** (`step_size`) and **the minimum notional**. A
  position below the venue's minimum, or off its size grid, is not a trade
  anybody could place, and counting it inflates a result. PRD §41 rule 9 governs
  any economic evaluation.
- **the assets** (`base_asset`, `quote_asset`) and **the contract size**, without
  which a perp's quantity is a number with no unit.
- **the trading status**, because an instrument that is halted is not one a
  signal can be opened on, and its absence and its halt are different facts.

Today the system knows a market by `venue`, `symbol` and `market_type` and
nothing else.

## Acceptance

- an exchange's instrument payload is normalized into instrument values, with
  the venue's own field names left at the boundary;
- a payload missing a field this requirement names is refused rather than
  defaulted — a tick size guessed at is worse than one absent;
- decimal quantities stay decimal end to end, with no float in the path;
- instruments are stored on the canonical plane and read back identically;
- an instrument recorded twice does not appear twice;
- the API serves an instrument's rules with the market it belongs to, and the
  in-memory and lakehouse repositories answer alike;
- no endpoint's existing fields change.

## Trace

<!-- trace:begin -->
- **Specs:** [[SPEC-060-instrument-metadata]]
- **Outcomes:** [[OUT-2026-09-10-requirement-instrument-metadata]], [[OUT-2026-09-10-spec-instrument-metadata]]
<!-- trace:end -->

## Notes

Extracted by hand. The PRD line is a deliverable with no section behind it, and
`tools/extract_prd.py` would have written `ACCEPTANCE-NOT-SPECIFIED`. The
acceptance above is **derived**, and the derivation is the body of this note: each
field is there because something downstream cannot be correct without it, not
because exchanges publish it.

**Using the rules is deliberately not in scope.** Rounding a fill to a valid
tick, refusing a size below the minimum, and skipping a halted instrument are
each a change to the backtest's execution model, and each deserves its own
requirement rather than arriving as a side effect of an ingestion deliverable.
What is in scope is that the numbers exist, are right, and are reachable — so
this does not repeat the pattern [[REQ-STORE-001]], [[REQ-TBL-001]] and
[[REQ-BIAS-011]] each recorded in turn, where a mechanism was built and nothing
used it: the API serves these the moment they are stored.

Fetching the payload over HTTP is out of scope for the same reason the rest of
[[REQ-WP-003]] keeps the wire behind a `Transport` protocol — the normalizer
takes a payload, and where the payload came from is the caller's business.
