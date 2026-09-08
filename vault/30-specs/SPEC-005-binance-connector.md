---
id: SPEC-005-binance-connector
requirement: REQ-WP-003
speckit_path: specs/005-binance-connector/spec.md
status: draft
---

## Summary

Native Binance connector per [[ADR-004]]: normalization into [[REQ-WP-002]]'s
canonical models, order-book reconstruction following PRD §11.1 with an honest
health state, and a stream lifecycle that survives the venue's 24-hour limit.

Tests replay committed fixtures and open no socket. Liquidations are out of
scope — the stream that carries them is unreachable from this network, and the
spec says so rather than claiming them.

## Links

- Requirement: [[REQ-WP-003]]
- Decision: [[ADR-004]]
- Depends on: [[REQ-WP-002]]
