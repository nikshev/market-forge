---
id: OUT-2026-09-11-requirement-bybit
step: requirement
records: [REQ-WP-043]
commit: null
---

## What was done

`vault/10-requirements/REQ-WP-043.md`, from PRD §5.2 and §45's Phase 5, read
against the Bybit v5 documentation the PRD's own reference list names.

## What was decided

- **The product is linear perpetuals, not spot.** §5.2 says "Bybit linear
  perps" in as many words. A first probe went to the spot stream, which would
  have been a working connector for a market this project's universe does not
  include.
- **The fixtures are recorded.** [[ADR-004]] settled this for Binance — a live
  message carries fields the documentation does not mention, and a hand-written
  sample encodes the author's misunderstanding as a passing test. Verified that
  Bybit's public stream needs no account: it delivered real trades on a probe.
- **The venue difference that matters is the taker side.** Binance sends `m`,
  whether the *buyer* was the maker, so the aggressor is derived. Bybit sends
  `S`, which its documentation calls the taker side directly. Getting that
  backwards inverts every order-flow figure above it and shows no symptom — the
  same failure the transport's own sweep caught two commits ago, arriving from a
  second direction.
- **OKX stays a separate requirement.** Two connectors landing together would
  make a failure in either look like a failure of the idea.

## What is still open

- **Funding and open interest** arrive on other Bybit channels and belong with
  the derivatives path, which has readings and nothing writing them.
- **Private endpoints** would need credentials this project does not hold and
  does not want.
