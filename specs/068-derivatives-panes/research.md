# Phase 0 — Research

## 1. Where can the two lists meet?

**Decision**: a Python test that reads `panes.ts`.

**Rationale**: the registry is Python and the panes are TypeScript. A vitest
check would need the feature names in TypeScript — a copy, which would agree
with itself forever. Parsing the source is unglamorous and is the only place the
real lists touch.

## 2. What happens if the source changes shape?

**Decision**: the parser raises rather than returning nothing.

**Rationale**: found by the mutation sweep. Deleting the "nothing parsed" guard
changed no result, because no test ever handed the parser a source it could not
read — so the guard was real protection with no evidence behind it. The parser
is now a separate function and two tests hand it exactly those sources.

Without it, an unfamiliar declaration makes every assertion pass over an empty
list, and the check goes on being green while checking nothing.

## 3. Which four panes?

**Decision**: `open_interest_usd`, `funding_z`, `basis_bps`,
`liquidation_imbalance_5m`.

**Rationale**: PRD §27.3 names OI, funding, basis and liquidations. Each maps to
a registered feature; where a family offers several, the one chosen is the one a
reader reads for that pane's question — the level for open interest, the z-score
for funding, the basis in bps, the imbalance for liquidations.
