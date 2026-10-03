---
id: SPEC-127-markets-registered
requirement: REQ-WP-081
speckit_path: specs/127-markets-registered/spec.md
status: draft
---

## Summary

`/api/v1/markets` answers an empty list because nothing running writes the markets table. Each ingest
process knows its venue and symbol, so it registers its own market at start, once, with the market type
from the venue registry — and Binance's is `spot`, because its stream is the spot stream, whatever the
PRD's example alert says. No trading rules are registered; failure to register is a warning and never
stops ingest.

## Links

- Requirement: [[REQ-WP-081]]
- Built on: [[REQ-WP-021]], [[REQ-WP-075]], [[REQ-WP-076]]
