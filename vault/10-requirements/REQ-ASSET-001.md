---
id: REQ-ASSET-001
title: Asset identity and cross-venue instrument registry
type: work-package
prd_ref: "§18.13 Asset identity and normalization"
prd_lines: "3238-3277"
phase: null
status: draft
depends_on: []
tags: []
hard_gated: false
---

## Requirement

PRD §18.13: "Cross-chain/venue comparison is impossible without a strict asset
registry."

Required entities:

```text
Asset
AssetRepresentation
MarketPair
Pool
Venue
ProtocolDeployment
```

The relationship the registry must express, from the PRD's own example:

```text
ETH
  ├── native ETH Ethereum
  ├── WETH Ethereum
  ├── WETH Base
  └── Hyperliquid ETH market representation
```

**Do not merge wrapped, bridged or synthetic assets only by ticker.**

Asset mapping carries:

- canonical economic asset id;
- chain id;
- contract address/native marker;
- decimals;
- wrapper/underlying relationship;
- bridge issuer if relevant;
- stablecoin family;
- pricing source priority;
- confidence.

## Acceptance

- an asset is registered with a canonical economic id, and its representations
  carry chain id, contract address or a native marker, decimals, and the
  wrapper/underlying relationship;
- two representations sharing a ticker but differing in chain or contract remain
  distinct representations; merging by ticker alone never occurs;
- a representation with no declared relationship to a canonical asset is refused
  rather than assumed to be that asset;
- a market pair names its base and quote representations and the venue it trades
  on;
- a venue names its kind — order book, AMM pool, or on-chain CLOB — and, for
  on-chain venues, its protocol deployment;
- every mapping carries a confidence and a pricing source priority, both
  readable by a consumer;
- bridge issuer and stablecoin family are recorded where they apply and absent
  where they do not, and absent is distinguishable from unknown.

## Trace

<!-- trace:begin -->
- **Outcomes:** [[OUT-2026-09-08-requirement-cross-venue-acceptance]]
<!-- trace:end -->

## Notes

Hand-written rather than produced by `tools/extract_prd.py`, which walks the
work-package and phase lists. §18.13 is a specification section no work package
names: `REQ-WP-014`'s acceptance is logs, finality, reorgs, ABI decoding and RPC
health; `REQ-WP-015`'s is pool math, swap and mint/burn decoding, tick state and
depth simulation. Neither includes asset identity, and `REQ-WP-016`'s body names
"canonical instrument mapping" without §17 defining it anywhere.

Extracted and scoped in
`docs/superpowers/specs/2026-09-08-cross-venue-acceptance-design.md`, whose
acceptance criteria the repository owner approved on 2026-09-08. Same precedent
as `REQ-API-001` for §28.

`Pool` and `ProtocolDeployment` already exist under `REQ-WP-014` and
`REQ-WP-015`; this registry references them rather than duplicating them.
