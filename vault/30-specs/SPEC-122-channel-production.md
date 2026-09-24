---
id: SPEC-122-channel-production
requirement: REQ-WP-077
speckit_path: specs/122-channel-production/spec.md
status: draft
---

## Summary

The channel production loop is the missing "worker" from PRD §6.2's MVP compose list.
It reads bars at every configured timeframe (from [[REQ-WP-073]]'s resampler) and
drives `record_replay` to populate `channel_snapshots`, `signals`,
`confirmed_extrema`, `extremum_candidates`. This is the "deployment work"
[[REQ-PIPE-001]] deliberately excluded.

## Links

- Requirement: [[REQ-WP-077]]
- Depends on: [[REQ-WP-073]], [[REQ-PIPE-001]]
