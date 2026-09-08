---
id: OUT-2026-09-08-spec-cross-venue
step: spec
records: [REQ-WP-016]
commit: null
---

## What was done

`specs/023-cross-venue/spec.md`: four user stories, 16 functional requirements,
11 success criteria, two ADRs. This is the requirement that carried the
`ACCEPTANCE-NOT-SPECIFIED` marker; its criteria were derived from PRD §17 and
approved before the spec was written.

## What was decided

- **A prohibition becomes a structural fact, twice.** §17.2 forbids converting a
  lagged correlation into a trading rule without out-of-sample validation, and
  §18.14 forbids applying §17.3's mid-based basis to an AMM. Neither is
  checkable as written. The first becomes an import ban over the signal,
  alerting and stop packages ([[ADR-040]]); the second becomes a refusal, with
  `executable_basis_bps` at a caller-supplied notional as the answer instead.
- **Executable prices are supplied, not computed** ([[ADR-039]]). Fees, gas and
  MEV margins are venue-specific operational inputs; an engine that assumed them
  would hide those assumptions at every call site. This engine ranks them.
- **No default notional.** At zero size every venue costs the same, so a default
  would make the best-execution answer arbitrary while looking definite.
- **Comparability comes from [[REQ-ASSET-001]]'s registry**, never from tickers —
  which is why that requirement was built first.

## What is still open

- **§17.1's volume/depth weighted median is not built**; the PRD marks it
  experimental.
- **No second CEX connector.** Binance and Uniswap v3 are the venue pair, and
  quotes are supplied to the engine rather than fetched.
