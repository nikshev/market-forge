---
id: SPEC-154-live-bars
requirement: REQ-WP-102
speckit_path: specs/154-live-bars/spec.md
status: draft
---

## Summary

Ingest daemons publish their forming and final 1m bars to Redpanda; the API relays them over `/ws/market` with a thirty-minute cache; the 1m chart draws them live.

## Links

- Requirement: [[REQ-WP-102]]
