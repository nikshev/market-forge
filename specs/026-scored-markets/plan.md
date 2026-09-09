# Implementation Plan: A ranked market list and a signal's contribution factors

**Branch**: `us-001-004-scored-markets` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

## Summary

The score reaches the surface: the repository stores one per market, the market
list is ordered by PRD §43's rank score, and a signal's detail carries §22.4's
explanation — with a panel that shows all six groups.

## Technical Context

**Language/Version**: Python 3.12 and TypeScript.

**Primary Dependencies**: `channelflow.scoring` (REQ-SCORE-001). Nothing new.

**Storage**: `InMemoryRepository`, as every other endpoint uses (ADR-019).

**Testing**: pytest over the FastAPI test client; vitest for the panel.

**Target Platform**: `src/channelflow/api/`, `apps/web/src/`.

**Constraints**: FR-003 and FR-008 both carry [[ADR-044]]'s distinction to the
surface; FR-010 keeps the API computing nothing.

**Scale/Scope**: one new module each side, 10 API tests and 4 panel tests.

## Constitution Check

- **VI (every feature is documented)** — a score arrives with the contributions
  behind it, so PRD §0 item 10 is answerable from the response.
- **IX (no order placement)** — read-only, like every other endpoint.
- **XI (results are reproducible)** — the order is total: rank score, then name.
- **XIV** — traces to REQ-US-001 and REQ-US-004.

**Gate result: PASS.**

## Project Structure

```text
src/channelflow/api/
├── ranking.py       # NEW: 43's order over the market list
├── repositories.py  # + ScoredSetup, add_setup_score, setup_score
├── schemas.py       # + MarketOut scores, FactorOut, ExplanationOut
└── routes.py        # markets ordered; signal detail carries the explanation

apps/web/src/
├── Explanation.tsx  # NEW: 27.4's panel over 22.4's items
└── types.ts         # + the six groups and the wire shapes
```

**Structure Decision**: the ordering lives in `ranking.py`, not in the handler,
for the reason `channels.py` holds the refit — the endpoints read and shape, and
anything with a rule in it belongs where a test can reach it without a client.

## Approach

**Absent is not zero, twice.** An unscored market sorts after every scored one
and reports nulls; a missing family appears among the missing and never among
the negative factors. Both are [[ADR-044]]'s distinction at the surface, where a
reader would otherwise see a number and no way to tell.

**The unscored tail is ordered by name.** Every unscored market ties, and a tie
resolved by the repository's own order is a list that happens to be stable
today.

**The panel renders all six groups, always.** A group left off because it had no
data reads as "not relevant here", which is the opposite of what happened.

**The explanation is not nested with the outcome.** §27.4 requires the later
outcome "visually separated so it cannot be confused with information available
at signal time" — nesting would make that impossible for any UI, not only this
one.

## Complexity Tracking

> No violations.
