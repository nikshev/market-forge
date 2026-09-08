---
id: REQ-ASSET-001
title: Asset identity and cross-venue instrument registry
type: work-package
prd_ref: "§18.13 Asset identity and normalization"
prd_lines: "3238-3277"
phase: null
status: implemented
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
- **Specs:** [[SPEC-022-asset-registry]]
- **Tests:**
    - `tests/unit/assets/test_registry.py::test_a_chain_deeper_than_any_real_wrapping_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_missing_confidence_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_native_marker_and_a_contract_address_are_mutually_exclusive`
    - `tests/unit/assets/test_registry.py::test_a_pair_against_itself_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_pair_names_both_sides_and_its_venue`
    - `tests/unit/assets/test_registry.py::test_a_pair_on_an_unregistered_venue_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_provenance_filter_is_expressible`
    - `tests/unit/assets/test_registry.py::test_a_representation_naming_an_unregistered_asset_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_representation_without_a_declared_asset_cannot_be_built`
    - `tests/unit/assets/test_registry.py::test_a_shared_ticker_does_not_make_two_assets_one`
    - `tests/unit/assets/test_registry.py::test_a_tie_in_priority_is_broken_by_key`
    - `tests/unit/assets/test_registry.py::test_a_wrapper_chain_resolves_to_its_root`
    - `tests/unit/assets/test_registry.py::test_a_wrapper_cycle_is_refused`
    - `tests/unit/assets/test_registry.py::test_a_wrapper_of_a_wrapper_resolves`
    - `tests/unit/assets/test_registry.py::test_an_ambiguous_ticker_lookup_refuses`
    - `tests/unit/assets/test_registry.py::test_an_onchain_venue_without_a_deployment_is_refused`
    - `tests/unit/assets/test_registry.py::test_an_order_book_venue_with_a_deployment_is_refused`
    - `tests/unit/assets/test_registry.py::test_an_unambiguous_ticker_lookup_works`
    - `tests/unit/assets/test_registry.py::test_not_applicable_and_unknown_are_distinguishable`
    - `tests/unit/assets/test_registry.py::test_omitting_a_three_state_field_is_refused`
    - `tests/unit/assets/test_registry.py::test_registering_the_same_chain_and_contract_twice_is_refused`
    - `tests/unit/assets/test_registry.py::test_representations_order_by_pricing_priority_totally_and_stably`
    - `tests/unit/assets/test_registry.py::test_the_assets_package_cannot_consult_a_clock_or_open_a_socket`
    - `tests/unit/assets/test_registry.py::test_the_prds_own_eth_example_resolves_to_one_asset`
    - `tests/unit/assets/test_registry.py::test_two_tokens_sharing_a_ticker_on_different_chains_stay_distinct`
- **Code:**
    - `src/channelflow/assets/__init__.py`
    - `src/channelflow/assets/models.py`
    - `src/channelflow/assets/registry.py`
- **Outcomes:** [[OUT-2026-09-08-implement-asset-registry]], [[OUT-2026-09-08-plan-asset-registry]], [[OUT-2026-09-08-requirement-cross-venue-acceptance]], [[OUT-2026-09-08-spec-asset-registry]]
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
