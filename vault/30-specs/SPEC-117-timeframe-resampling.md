---
id: SPEC-117-timeframe-resampling
requirement: REQ-WP-073
speckit_path: specs/117-timeframe-resampling/spec.md
status: draft
---

## Summary

§5.1 names four timeframes and §31 makes the list configuration, but the
deployment writes one series — one-minute bars — because the ingest daemon
carries a single `timeframe_ns`. The spec builds the rest by resampling the
stored minutes rather than by running a second builder against the trade stream:
idempotent, runnable over history, nothing added to the socket path. Its price is
an input that can be incomplete without being late, so completeness is a tested
condition rather than an assumption, and the two boundaries floor division gets
wrong — a week that would open on Thursday, a calendar month that has no
nanosecond count at all — are stated and handled rather than discovered.

## Links

- Requirement: [[REQ-WP-073]]
- Constraint: [[REQ-NRT-UPSAMPLE]]
