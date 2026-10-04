---
id: SPEC-131-channel-as-fitted
requirement: REQ-WP-082
speckit_path: specs/131-channel-as-fitted/spec.md
status: draft
---

## Summary

The chart drew the channel as three flat lines across the whole history, because the API dropped the fit's
slope and the page repeated the current levels for every bar; the owner could not see it. The channel is a
log-linear band over its lookback window, exact from the current levels and the slope. Expose the slope, draw
the sloped lines over the window ending at the snapshot's own bar, open the view on the recent bars and make
the lines legible.

## Links

- Requirement: [[REQ-WP-082]]
- Built on: [[REQ-WP-009]], [[REQ-WP-006]]
