---
id: SPEC-141-detector-gap-policy
requirement: REQ-WP-087
speckit_path: specs/141-detector-gap-policy/spec.md
status: draft
---

## Summary

The extremum detector and channel fit must not straddle gaps in the bar series. On a hole (> `gap_threshold` missing bars, default 1), the detector resets its state (direction, running extreme, candidate) and the channel fits only to bars after the hole. No confirmation straddles a hole; channel snapshot is absent until `lookback` contiguous bars exist. `gap_threshold` is configuration (default 1). Confirmed extremum carries `confirmation_lag_ns` (time) in addition to bars. Policy 2 (restart at gap) assumed per requirement recommendation; owner confirmation needed.

## Links

- Requirement: [[REQ-WP-087]]
- Built on: [[REQ-WP-086]], [[REQ-WP-006]], [[REQ-WP-019]]