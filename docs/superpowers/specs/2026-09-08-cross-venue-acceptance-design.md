# Cross-venue acceptance criteria — design

**Date**: 2026-09-08
**Status**: approved
**Requirements affected**: `REQ-WP-016` (existing, `draft`), `REQ-ASSET-001` (new)

## Why this document exists

`REQ-WP-016` carries the `ACCEPTANCE-NOT-SPECIFIED` marker. PRD §17 describes a
cross-venue engine in four subsections but states no acceptance criteria, and
`/sdd-spec` refuses to specify a requirement in that state: the criteria must be
written by a human from the PRD section, not invented by the process that will
then be measured against them.

This document records the criteria that were derived, the four decisions taken
in deriving them, and the reasoning for each — so that a reader who disagrees
with a criterion can see what it was chosen over.

## What the PRD actually says

§17 has four subsections:

- **§17.1 Consensus price** — "robust consensus mid from selected high-liquidity
  venues", by median of normalized mids; a volume/depth weighted median is named
  as experimental.
- **§17.2 Lead-lag features** — per-venue returns over 1/5/10 s, pairwise lagged
  correlations, and one prohibition: "Do not convert correlation to trading rule
  without OOS validation."
- **§17.3 Cross-venue basis** — `basis_bps(venue_i) = 10000 * (mid_i /
  consensus_mid - 1)`.
- **§17.4 Fragmentation / liquidity** — depth by venue at 10/25/50 bps, best
  effective execution venue for fixed notional sizes, concentration of liquidity
  across venues.

`REQ-WP-016`'s body, extracted verbatim from the PRD's work-package list, names
three things: canonical instrument mapping, consensus price, basis.

**"Canonical instrument mapping" is not defined in §17 at all.** It is defined in
§18.13 — an asset identity registry of six entities and nine mapping fields,
carrying its own prohibition: "Do not merge wrapped, bridged or synthetic assets
only by ticker."

§18.14 adds a second prohibition that bears directly on §17.3: "Never compare a
CEX top-of-book quote against an AMM infinitesimal spot quote and call it
arbitrage." Its comparison unit is executable economics at a target notional `N`.

## Four decisions

### 1. Scope is all four §17 subsections

`REQ-WP-016`'s body names three deliverables; §17 has four subsections. The
criteria cover all four. Lead-lag and fragmentation are part of the PRD section
the work package points at, and four merged work packages have already deferred
specific things here — funding and basis dispersion (`REQ-WP-013`), cross-venue
book consolidation (`REQ-WP-004`), §44A.15's context (`REQ-WP-020`). Leaving two
subsections out would mean those deferrals point at nothing.

### 2. Both kinds of basis, separately named

§17.3 defines basis over mids. §18.14 forbids exactly that comparison when one
side is an AMM. Both are honoured, under different names:

- `basis_bps` — §17.3's formula, over mids, for order-book venues only;
- `executable_basis_bps(N)` — §18.14's, from executable prices at a target
  notional, for any pair involving an AMM.

The mid-based figure is **refused** when either side is an AMM, rather than
computed and captioned. A caption does not travel with a number; a refusal does.

Both halves of the executable comparison already exist: `depth_within_bps`
(`REQ-WP-004`) for the order book, `depth_to_bps` (`REQ-WP-015`) for the AMM.

### 3. The full §18.13 registry

Six entities — Asset, AssetRepresentation, MarketPair, Pool, Venue,
ProtocolDeployment — and the nine mapping fields §18.13 lists. `Pool` and
`ProtocolDeployment` already exist in `REQ-WP-014`/`REQ-WP-015` and are
referenced rather than duplicated.

### 4. The registry is its own requirement

§18.13 answers "is this the same asset"; §17 answers "how do these venues
relate". They are different subsystems, the PRD keeps them in different
top-level sections, and **no work package names §18.13** — `REQ-WP-014`'s
acceptance is logs, finality, reorgs, ABI decoding and RPC health;
`REQ-WP-015`'s is pool math, swap and mint/burn decoding, tick state and depth
simulation. Neither includes asset identity.

So §18.13 becomes `REQ-ASSET-001`, and `REQ-WP-016` depends on it. The precedent
is `REQ-API-001`, extracted from §28 for the same reason: a specification
section the work-package list does not cover.

The cost of not splitting is visible in this repository already —
`REQ-WP-019` sits at `tested` because two of its five criteria need subsystems
that were not built with it. One requirement covering both an asset registry and
cross-venue analytics would sit the same way.

## REQ-ASSET-001 — acceptance criteria

1. An asset is registered with a canonical economic id, and its representations
   carry chain id, contract address or a native marker, decimals, and the
   wrapper/underlying relationship.
2. Two representations sharing a ticker but differing in chain or contract remain
   distinct representations; merging by ticker alone never occurs.
3. A representation with no declared relationship to a canonical asset is refused
   rather than assumed to be that asset.
4. A market pair names its base and quote representations and the venue it trades
   on.
5. A venue names its kind — order book, AMM pool, or on-chain CLOB — and, for
   on-chain venues, its protocol deployment.
6. Every mapping carries a confidence and a pricing source priority, both
   readable by a consumer.
7. Bridge issuer and stablecoin family are recorded where they apply and absent
   where they do not, and absent is distinguishable from unknown.

Criterion 7 is the one worth defending. "There is no bridge issuer, because this
is a native asset" and "we do not know who issued this bridge" are different
facts. Conflating them means a consensus price will one day include an asset
whose provenance nobody checked, and nothing will have said so.

## REQ-WP-016 — acceptance criteria

**Consensus price (§17.1)**

1. A consensus mid is the median of normalized mids across the selected venues,
   and the result names the venues that contributed.
2. A venue whose mid is missing, or older than a configurable staleness
   tolerance at the instant asked about, does not contribute — and the
   contributor count is reported. The tolerance is configuration, as every
   other threshold in this repository is (Principle X).
3. A consensus over fewer than two contributing venues is refused.

**Basis (§17.3, §18.14)**

4. `basis_bps(venue_i) = 10000 * (mid_i / consensus_mid - 1)` is computed for
   each contributing venue.
5. Mid-based basis is refused when either side is an AMM, and
   `executable_basis_bps(N)` is computed instead, from executable prices at a
   notional `N` supplied by the caller. There is no default `N`: the right size
   depends on what the answer is for, and a default would be a trading
   assumption hidden in a helper.

**Lead-lag (§17.2)**

6. Per-venue returns over 1/5/10 s windows and pairwise lagged correlations are
   computed from data available at the instant asked about.
7. Lead-lag outputs are marked research-only, and no signal-path module imports
   them — asserted over the source.

**Fragmentation (§17.4)**

8. Depth by venue at 10/25/50 bps is reported, each venue measured by its own
   executable-depth measure.
9. The best effective execution venue for a fixed notional is identified from
   all-in cost, not from top-of-book price.
10. Liquidity concentration across venues is reported.

**Throughout**

11. Every output is computed from data available at the instant asked about; no
    venue's later value is used.

### Two criteria worth defending

**Criterion 3.** A median over one venue is that venue's mid wearing a better
name. The word "consensus" would then be doing work the arithmetic is not, and
every consumer downstream would read agreement where there was only one opinion.
Refusing follows the same reasoning as `ADR-026` (a z-score refuses rather than
returning zero) and `ADR-036` (an unreachable depth is a refusal, not a smaller
number).

**Criterion 7.** §17.2's prohibition — "Do not convert correlation to trading
rule without OOS validation" — cannot be checked as written. What can be checked
is that the signal path does not import the module. This is the third use of a
shape that has already worked twice here: `ADR-022`, where a transform declares
whether it looks forward and the production path refuses the ones that do, and
`ADR-027`, where §16.2's price/OI matrix is a label nothing acts on.

**Criterion 9** carries the section's most expensive mistake. The venue with the
best top-of-book price and the venue with the best actual execution cost are
different venues as soon as size stops being infinitesimal. §18.14 forbids that
comparison; the criterion states the prohibition as a requirement.

## What these criteria deliberately do not require

- **A second CEX connector.** No work package in the PRD builds one — Bybit and
  OKX are named in §17.2 and appear in no WP-list entry. The real venue pair
  available in this project is Binance and Uniswap v3, which is genuinely two
  venues and is enough to exercise every criterion above.
- **§17.1's volume/depth weighted median.** The PRD marks it experimental; the
  median of normalized mids is what is required.
- **Any trading rule derived from lead-lag.** Criterion 7 forbids it until OOS
  validation exists, which is `REQ-WP-017`'s and `REQ-WP-018`'s territory.

## Consequences

- `REQ-WP-016` can leave `draft`; both requirements can go through the normal
  `/sdd-spec` → `/sdd-plan` → `/sdd-tasks` → `/sdd-implement` pipeline.
- `REQ-ASSET-001` is a dependency of `REQ-WP-016` and must land first.
- Four merged work packages' deferrals now point at criteria rather than at a
  marker.
