---
id: SPEC-120-markets-route
requirement: REQ-WP-075
speckit_path: specs/120-markets-route/spec.md
status: draft
---

## Summary

§27.1's overview route is the one view §28.1 already has the read for: one row
per market, in the order §43 ranked them, with an unscored market plainly
unscored rather than rendered as a zero. The spec keeps the view from inventing
anything — no new aggregate, no re-sort, no second timeframe list — and settles
the two decisions the PRD leaves open: the root path renders the same view, and
a row is a link to `/chart/<venue>/<symbol>?tf=<chosen>` whose destination is
byte for byte the deep link a reader could have pasted.

## Links

- Requirement: [[REQ-WP-075]]
- Depends on: [[REQ-WP-074]], [[REQ-US-001]]
