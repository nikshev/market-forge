---
id: SPEC-027-deep-link-overlays
requirement: REQ-US-002
speckit_path: specs/027-deep-link-overlays/spec.md
status: draft
---

## Summary

REQ-US-002's two clauses, both of which the chart only half kept: the deep link
carried the signal's instant but the view was fitted to the whole history, and
nothing carried PRD §27.2's overlays at all.

The alert now declares which layers were on, the link names them sorted and
deduplicated so one alert is one link, and the chart opens centred on the bar
covering the instant with exactly those layers drawn.

[[ADR-045]] settles the mangled case, extending [[ADR-020]]. A channel mode is
one token — readable or not. An overlay list can be *partly* readable, and a
restored subset looks restored while missing whichever layer the reader most
needed. So any unrecognised name discards the list whole, and the page says
which of the three states it is in.

## Links

- Requirement: [[REQ-US-002]]
- Decision: [[ADR-045]], extending [[ADR-020]]
- Builds on: [[REQ-WP-008]], [[REQ-WP-009]]
