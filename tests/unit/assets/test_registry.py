"""PRD section 18.13's registry (REQ-ASSET-001).

"Cross-chain/venue comparison is impossible without a strict asset
 registry."
"Do not merge wrapped, bridged or synthetic assets only by ticker."
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from channelflow.assets import (
    Absence,
    AmbiguousTicker,
    Asset,
    AssetRegistry,
    DuplicateRepresentation,
    MarketPair,
    ProtocolDeploymentRef,
    UnknownAsset,
    UnknownVenue,
    Venue,
    VenueKind,
    WrapperCycle,
)

from .conftest import BASE, ETHEREUM, HYPERLIQUID, representation


@pytest.mark.trace("REQ-ASSET-001")
def test_the_prds_own_eth_example_resolves_to_one_asset(
    eth_registry: AssetRegistry,
) -> None:
    """SC-001. Four representations, one economic thing."""
    keys = [
        f"{ETHEREUM}:native",
        f"{ETHEREUM}:0xc02aaa39",
        f"{BASE}:0x4200000006",
        f"{HYPERLIQUID}:0xhleth",
    ]

    assert all(eth_registry.canonical_asset(k).asset_id == "ETH" for k in keys)
    assert eth_registry.same_asset(keys[0], keys[2])


@pytest.mark.trace("REQ-ASSET-001")
def test_two_tokens_sharing_a_ticker_on_different_chains_stay_distinct(
    eth_registry: AssetRegistry,
) -> None:
    """SC-002, FR-004, PRD section 18.13's prohibition.

    WETH on Ethereum and WETH on Base share a ticker and are different tokens.
    They happen to be the same *asset* here because someone declared it -- and
    that declaration is the only reason.
    """
    ethereum_weth = f"{ETHEREUM}:0xc02aaa39"
    base_weth = f"{BASE}:0x4200000006"

    assert ethereum_weth != base_weth
    assert eth_registry.representations[ethereum_weth].address != (
        eth_registry.representations[base_weth].address
    )
    assert eth_registry.same_asset(ethereum_weth, base_weth), "declared, not inferred"


@pytest.mark.trace("REQ-ASSET-001")
def test_a_shared_ticker_does_not_make_two_assets_one() -> None:
    """SC-002, FR-004, ADR-038 -- the case the prohibition is actually about.

    Native USDC and a bridged lookalike share a ticker and are different
    assets with different depeg risk. A consensus price across both reports
    agreement that does not exist, and the number looks like every other one.
    """
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="USDC", name="USD Coin"))
    registry.add_asset(Asset(asset_id="USDC.bridged", name="Bridged USD Coin"))

    registry.add_representation(
        representation(
            asset_id="USDC",
            chain_id=ETHEREUM,
            ticker="USDC",
            address="0xA0b86991",
            decimals=6,
            stablecoin_family="usd",
        )
    )
    registry.add_representation(
        representation(
            asset_id="USDC.bridged",
            chain_id=BASE,
            ticker="USDC",
            address="0xd9aAEc",
            decimals=6,
            bridge_issuer="some-bridge",
            stablecoin_family="usd",
        )
    )

    assert not registry.same_asset(f"{ETHEREUM}:0xa0b86991", f"{BASE}:0xd9aaec")


@pytest.mark.trace("REQ-ASSET-001")
def test_a_representation_without_a_declared_asset_cannot_be_built() -> None:
    """SC-003, FR-002. Enforced by the type: there is no code path that
    infers one."""
    with pytest.raises(ValidationError):
        representation(asset_id="", chain_id=ETHEREUM, ticker="ETH", is_native=True)


@pytest.mark.trace("REQ-ASSET-001")
def test_a_representation_naming_an_unregistered_asset_is_refused() -> None:
    """SC-003, FR-003, the spec's second edge case.

    Refused at registration rather than at read time: a dangling reference
    would otherwise surface as a consensus price over an asset nobody defined.
    """
    registry = AssetRegistry()

    with pytest.raises(UnknownAsset, match="not registered"):
        registry.add_representation(
            representation(asset_id="GHOST", chain_id=ETHEREUM, ticker="GHO", address="0x1")
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_an_ambiguous_ticker_lookup_refuses() -> None:
    """SC-004, FR-005, ADR-038.

    Returning the first, the most confident or the most recently registered
    would be merging by ticker with extra steps.
    """
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="USDC", name="USD Coin"))
    registry.add_asset(Asset(asset_id="USDC.bridged", name="Bridged USD Coin"))
    registry.add_representation(
        representation(asset_id="USDC", chain_id=ETHEREUM, ticker="USDC", address="0xA", decimals=6)
    )
    registry.add_representation(
        representation(
            asset_id="USDC.bridged", chain_id=BASE, ticker="USDC", address="0xB", decimals=6
        )
    )

    with pytest.raises(AmbiguousTicker, match="forbids merging"):
        registry.by_ticker("USDC")


@pytest.mark.trace("REQ-ASSET-001")
def test_an_unambiguous_ticker_lookup_works(eth_registry: AssetRegistry) -> None:
    """FR-005. The rule withholds convenience where it would be wrong, not
    everywhere -- a lookup that always refused would be useless."""
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="ETH", name="Ether"))
    registry.add_representation(
        representation(asset_id="ETH", chain_id=ETHEREUM, ticker="ETH", is_native=True)
    )

    assert registry.by_ticker("eth").asset_id == "ETH"


@pytest.mark.trace("REQ-ASSET-001")
def test_registering_the_same_chain_and_contract_twice_is_refused(
    eth_registry: AssetRegistry,
) -> None:
    """SC-005, FR-006, the spec's first edge case.

    One chain and contract identify one token, so a repeat means two sources
    disagree about it -- and letting the second win silently is how a registry
    drifts from the chain.
    """
    with pytest.raises(DuplicateRepresentation, match="disagree"):
        eth_registry.add_representation(
            representation(asset_id="ETH", chain_id=ETHEREUM, ticker="WETH", address="0xC02AAA39")
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_not_applicable_and_unknown_are_distinguishable(
    eth_registry: AssetRegistry,
) -> None:
    """SC-006, FR-007, ADR-037.

    Native ETH cannot have a bridge issuer. The Hyperliquid representation has
    one and nobody recorded it. With a single `None` for both, a provenance
    filter is inexpressible.
    """
    native = eth_registry.representations[f"{ETHEREUM}:native"]
    hyperliquid = eth_registry.representations[f"{HYPERLIQUID}:0xhleth"]
    base_weth = eth_registry.representations[f"{BASE}:0x4200000006"]

    assert native.bridge_issuer is Absence.NOT_APPLICABLE
    assert hyperliquid.bridge_issuer is Absence.UNKNOWN
    assert base_weth.bridge_issuer == "base-bridge"
    assert native.bridge_issuer != hyperliquid.bridge_issuer


@pytest.mark.trace("REQ-ASSET-001")
def test_a_provenance_filter_is_expressible(eth_registry: AssetRegistry) -> None:
    """SC-006, ADR-037's payoff.

    "Every representation here has a known or inapplicable bridge issuer" is
    the statement a consensus price needs to be able to make about its inputs,
    and it is only checkable because the two absences are different values.
    """
    unchecked = [
        r for r in eth_registry.representations.values() if r.bridge_issuer is Absence.UNKNOWN
    ]

    assert [r.ticker for r in unchecked] == ["ETH"], "the Hyperliquid one"


@pytest.mark.trace("REQ-ASSET-001")
def test_omitting_a_three_state_field_is_refused() -> None:
    """SC-006, FR-008, ADR-037.

    No default. Someone adding a token decides whether the issuer is unknown or
    inapplicable at the moment they still know.
    """
    from channelflow.assets import AssetRepresentation

    with pytest.raises(ValidationError):
        AssetRepresentation(
            canonical_asset_id="ETH",
            chain_id=1,
            address="0x1",
            ticker="ETH",
            decimals=18,
            stablecoin_family=Absence.NOT_APPLICABLE,
            pricing_source_priority=0,
            confidence=1.0,
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_a_wrapper_chain_resolves_to_its_root(eth_registry: AssetRegistry) -> None:
    """SC-007, FR-009. WETH on Ethereum wraps native ETH."""
    root = eth_registry.root_of(f"{ETHEREUM}:0xc02aaa39")

    assert root.is_native
    assert root.key == f"{ETHEREUM}:native"


@pytest.mark.trace("REQ-ASSET-001")
def test_a_wrapper_of_a_wrapper_resolves(eth_registry: AssetRegistry) -> None:
    """The spec's third edge case: wrapped-bridged tokens exist."""
    eth_registry.add_representation(
        representation(
            asset_id="ETH",
            chain_id=BASE,
            ticker="wWETH",
            address="0xWRAPPED",
            wraps=f"{ETHEREUM}:0xc02aaa39",
            bridge_issuer="base-bridge",
        )
    )

    assert eth_registry.root_of(f"{BASE}:0xwrapped").key == f"{ETHEREUM}:native"


@pytest.mark.trace("REQ-ASSET-001")
def test_a_wrapper_cycle_is_refused() -> None:
    """SC-007, FR-009, the spec's fourth edge case. Naming the cycle beats
    looping on it."""
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="X", name="X"))
    registry.add_representation(
        representation(asset_id="X", chain_id=1, ticker="A", address="0xA", wraps="1:0xb")
    )
    registry.add_representation(
        representation(asset_id="X", chain_id=1, ticker="B", address="0xB", wraps="1:0xa")
    )

    with pytest.raises(WrapperCycle, match="loops"):
        registry.root_of("1:0xa")


@pytest.mark.trace("REQ-ASSET-001")
def test_a_chain_deeper_than_any_real_wrapping_is_refused() -> None:
    """FR-009, the bound beside the cycle check.

    With only the cycle check, removing it makes the traversal run for ever --
    and "no answer" is a far weaker signal than a wrong one. A bounded walk
    always terminates with something a test can read.
    """
    from channelflow.assets.registry import MAX_WRAPPER_DEPTH

    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="X", name="X"))
    depth = MAX_WRAPPER_DEPTH + 5
    for i in range(depth):
        registry.add_representation(
            representation(
                asset_id="X",
                chain_id=1,
                ticker=f"W{i}",
                address=f"0x{i:04x}",
                wraps=f"1:0x{i + 1:04x}" if i < depth - 1 else None,
            )
        )

    with pytest.raises(WrapperCycle, match="exceeded"):
        registry.root_of("1:0x0000")


@pytest.mark.trace("REQ-ASSET-001")
def test_a_pair_names_both_sides_and_its_venue(eth_registry: AssetRegistry) -> None:
    """FR-010."""
    eth_registry.add_asset(Asset(asset_id="USDC", name="USD Coin"))
    eth_registry.add_representation(
        representation(
            asset_id="USDC",
            chain_id=ETHEREUM,
            ticker="USDC",
            address="0xA0b8",
            decimals=6,
            stablecoin_family="usd",
        )
    )
    eth_registry.add_venue(Venue(venue_id="binance", kind=VenueKind.ORDER_BOOK))

    pair = eth_registry.add_pair(
        MarketPair(
            pair_id="binance:ETHUSDC",
            base_key=f"{ETHEREUM}:native",
            quote_key=f"{ETHEREUM}:0xa0b8",
            venue_id="binance",
        )
    )

    assert pair.base_key != pair.quote_key


@pytest.mark.trace("REQ-ASSET-001")
def test_a_pair_against_itself_is_refused() -> None:
    """SC-008, FR-010. A market against itself has no price."""
    with pytest.raises(ValidationError):
        MarketPair(pair_id="x", base_key="1:native", quote_key="1:native", venue_id="v")


@pytest.mark.trace("REQ-ASSET-001")
def test_an_onchain_venue_without_a_deployment_is_refused() -> None:
    """SC-009, FR-011.

    §18.14 compares an order book and an AMM differently, so a venue that
    cannot say which contract it is quoting cannot be compared at all.
    """
    with pytest.raises(ValidationError):
        Venue(venue_id="uniswap", kind=VenueKind.AMM_POOL)


@pytest.mark.trace("REQ-ASSET-001")
def test_an_order_book_venue_with_a_deployment_is_refused() -> None:
    """FR-011, the other direction: an order book has no contract to deploy,
    and accepting one would let a CEX masquerade as on-chain."""
    with pytest.raises(ValidationError):
        Venue(
            venue_id="binance",
            kind=VenueKind.ORDER_BOOK,
            deployment=ProtocolDeploymentRef(protocol="x", version="1", chain_id=1, address="0x1"),
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_a_pair_on_an_unregistered_venue_is_refused(eth_registry: AssetRegistry) -> None:
    """FR-010, FR-011."""
    with pytest.raises(UnknownVenue):
        eth_registry.add_pair(
            MarketPair(
                pair_id="x",
                base_key=f"{ETHEREUM}:native",
                quote_key=f"{BASE}:0x4200000006",
                venue_id="nowhere",
            )
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_representations_order_by_pricing_priority_totally_and_stably(
    eth_registry: AssetRegistry,
) -> None:
    """SC-010, FR-013.

    Total and stable: two registries built from the same data list them the
    same way, so a consensus price built on this ordering is reproducible
    (Principle XI).
    """
    first = [r.key for r in eth_registry.representations_of("ETH")]
    second = [r.key for r in eth_registry.representations_of("ETH")]

    assert first == second
    priorities = [eth_registry.representations[k].pricing_source_priority for k in first]
    assert priorities == sorted(priorities)


@pytest.mark.trace("REQ-ASSET-001")
def test_a_tie_in_priority_is_broken_by_key() -> None:
    """FR-013. Without a tie-break the ordering is not total, and two builds
    could differ."""
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="X", name="X"))
    registry.add_representation(
        representation(asset_id="X", chain_id=1, ticker="B", address="0xB", priority=5)
    )
    registry.add_representation(
        representation(asset_id="X", chain_id=1, ticker="A", address="0xA", priority=5)
    )

    assert [r.key for r in registry.representations_of("X")] == ["1:0xa", "1:0xb"]


@pytest.mark.trace("REQ-ASSET-001")
def test_a_missing_confidence_is_refused() -> None:
    """SC-010, FR-012, the same reasoning as ADR-015's registry: a field with a
    default is a field an author can forget to think about."""
    from channelflow.assets import AssetRepresentation

    with pytest.raises(ValidationError):
        AssetRepresentation(
            canonical_asset_id="ETH",
            chain_id=1,
            address="0x1",
            ticker="ETH",
            decimals=18,
            bridge_issuer=Absence.NOT_APPLICABLE,
            stablecoin_family=Absence.NOT_APPLICABLE,
            pricing_source_priority=0,
        )


@pytest.mark.trace("REQ-ASSET-001")
def test_a_native_marker_and_a_contract_address_are_mutually_exclusive() -> None:
    """FR-001. It is one or the other, and accepting both would make `key`
    ambiguous."""
    with pytest.raises(ValidationError):
        representation(asset_id="ETH", chain_id=1, ticker="ETH", is_native=True, address="0x1")
    with pytest.raises(ValidationError):
        representation(asset_id="ETH", chain_id=1, ticker="ETH")


@pytest.mark.trace("REQ-ASSET-001")
def test_the_assets_package_cannot_consult_a_clock_or_open_a_socket() -> None:
    """SC-011, FR-014."""
    package = Path(__file__).resolve().parents[3] / "src" / "channelflow" / "assets"
    modules = list(package.glob("*.py"))
    assert modules

    for module in modules:
        source = module.read_text()
        for forbidden in ("import time", "time.time", "datetime.now", "utcnow", "time.monotonic"):
            assert forbidden not in source, f"{module.name} reaches for a clock: {forbidden!r}"
        for forbidden in ("import requests", "import httpx", "web3", "aiohttp"):
            assert forbidden not in source, f"{module.name} opens a socket: {forbidden!r}"
