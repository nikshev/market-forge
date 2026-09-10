---
id: SPEC-060-instrument-metadata
requirement: REQ-WP-021
speckit_path: specs/060-instrument-metadata/spec.md
status: draft
---

## Summary

The system knows a market by `venue`, `symbol` and `market_type` and nothing
else. It does not know the smallest price the venue will quote, the smallest
quantity it will fill, the smallest notional it will accept, what a contract is
denominated in, or whether the instrument is trading at all.

PRD §45's Phase 1 asks for "basic market metadata;" and says nothing more, so
"basic" is derived from what breaks without it. Each field earns its place by a
downstream failure: a fill at an unquotable price is a fill at a price that does
not exist, and a position under the venue minimum is a trade nobody could place
— PRD §41 rule 9 makes both a correctness question rather than a display one.

Two boundaries are drawn deliberately.

**A missing rule is a refusal, not a default.** An absent tick size stops a
calculation; a guessed one produces a number that looks like a measurement.

**Using the rules is a separate requirement.** Rounding a fill, refusing a size
and skipping a halted instrument each change the backtest's execution model. The
spec says so out loud so the absence reads as a boundary rather than an
omission.

The one thing this does not defer is the consumer. Three requirements in this
repository have each recorded the same pattern — a mechanism built with nothing
using it — so the API serves an instrument's rules the moment they are stored.

## Links

- Requirement: [[REQ-WP-021]]
- The phase this unblocks: [[REQ-PHASE-1]]
- The boundary it normalizes at: [[REQ-WP-003]]
- Where it is stored and served: [[REQ-STORE-002]], [[REQ-API-001]]
