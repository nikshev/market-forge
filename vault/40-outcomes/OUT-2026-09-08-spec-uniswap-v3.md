---
id: OUT-2026-09-08-spec-uniswap-v3
step: spec
records: [REQ-WP-015]
commit: null
---

## What was done

`specs/021-uniswap-v3/spec.md`: five user stories, 16 functional requirements,
10 success criteria, two ADRs.

## What was decided

- **Canonical ordering is enforced in the rebuild** ([[ADR-035]]). PRD §18.7
  names the trap outright: every log in a block shares its timestamp, so a
  timestamp sort applies a swap before the mint that supplied its liquidity,
  and the resulting pool is plausible in every field.
- **A repeated log triple is refused**, not deduplicated. It is the same log
  ingested twice — two providers, or a backfill overlapping live ingestion —
  and silently dropping it would hide the bug while doubling a mint.
- **An unreachable depth target is a refusal** ([[ADR-036]]), carrying how far
  it got as data on the refusal rather than as the answer.
- **`Collect` is decoded and inert.** §18.7 calls it LP economics rather than
  liquidity state, and folding it into the tick map would corrupt state it is
  not part of.

## What is still open

- **Uniswap v4, Curve, Aerodrome, Hyperliquid** (§18.8 to §18.11) are out of
  scope.
- **No fee accounting**; `Collect` is decoded and excluded.
- **Depth is in pool tokens, not USD** — §18.16's valuation policy is separate.
