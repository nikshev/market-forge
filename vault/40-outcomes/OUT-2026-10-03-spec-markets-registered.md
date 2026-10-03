---
id: OUT-2026-10-03-spec-markets-registered
step: spec
records: [REQ-WP-081]
commit: null
---

## What was done

Specified [[REQ-WP-081]] as `specs/127-markets-registered/spec.md`: four stories, seven requirements.
Before writing it, the markets route, the repository's write path, the table schema, the venue registry
and the overview page were read, and the live endpoint was asked: `{"markets":[]}`.

## What was decided

- **The daemon registers its own market.** It is the one component configured with the venue and the
  symbol. A separate registrar would be told the same list twice, and this repository has already found
  two lists of one thing disagreeing ([[REQ-WP-078]]).
- **The market type comes from the venue registry, and Binance is `spot`.** Its daemon connects to
  `stream.binance.com`, the spot stream; PRD §26.1's example says "Binance Perp". Calling it `perp`
  would be the convenient answer and would put a false label on the first screen. A test ties the type
  to the stream URL so the two cannot drift apart silently.
- **No trading rules.** Nothing reads them; only Binance has a normalizer; a network call at start-up for
  unused fields is a new way for ingest to fail.
- **Failure is soft and not retried in a loop.** Ingest is the product; the overview is not.
- **A racing duplicate is tolerated, not prevented.** The read keeps the latest row per key, so a
  duplicate cannot reach the list; making the table refuse one would need a lock this stack does not have.

## What is still open

- Where in `main` to register so the soft failure is testable without a catalog (plan).
- Whether `add_market`'s no-rules row should move beside `market_row` so there is one definition of it
  (plan; today it lives in the API's repository, and ingest must not import the API).
- The overview's heading still says "ChannelFlow" while the product is now Market Forge: branding, out
  of scope here, noted.
