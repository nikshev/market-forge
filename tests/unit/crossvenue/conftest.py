"""Venues quoting one asset (REQ-WP-016)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from channelflow.assets import (
    Absence,
    Asset,
    AssetRegistry,
    AssetRepresentation,
    ProtocolDeploymentRef,
    Venue,
    VenueKind,
)
from channelflow.crossvenue import ExecutableQuote, VenueQuote

SECOND_NS = 1_000_000_000
BASE_NS = 1788838800000000000
ETHEREUM = 1

BINANCE_KEY = "0:native"
UNISWAP_KEY = f"{ETHEREUM}:0xc02aaa39"
OKX_KEY = "0:0xokx"


def at(second: int) -> int:
    return BASE_NS + second * SECOND_NS


def representation(
    *, key_chain: int, address: str | None, ticker: str, native: bool, priority: int
):
    return AssetRepresentation(
        canonical_asset_id="ETH",
        chain_id=key_chain,
        address=address,
        is_native=native,
        ticker=ticker,
        decimals=18,
        bridge_issuer=Absence.NOT_APPLICABLE,
        stablecoin_family=Absence.NOT_APPLICABLE,
        pricing_source_priority=priority,
        confidence=1.0,
    )


@pytest.fixture
def registry() -> AssetRegistry:
    """One asset, three representations — two CEX markets and a pool."""
    reg = AssetRegistry()
    reg.add_asset(Asset(asset_id="ETH", name="Ether"))
    reg.add_asset(Asset(asset_id="BTC", name="Bitcoin"))
    reg.add_venue(Venue(venue_id="binance", kind=VenueKind.ORDER_BOOK))
    reg.add_venue(Venue(venue_id="okx", kind=VenueKind.ORDER_BOOK))
    reg.add_venue(
        Venue(
            venue_id="uniswap",
            kind=VenueKind.AMM_POOL,
            deployment=ProtocolDeploymentRef(
                protocol="uniswap_v3", version="1.0.0", chain_id=ETHEREUM, address="0xPOOL"
            ),
        )
    )
    reg.add_representation(
        representation(key_chain=0, address=None, ticker="ETH", native=True, priority=0)
    )
    reg.add_representation(
        representation(key_chain=0, address="0xokx", ticker="ETH", native=False, priority=1)
    )
    reg.add_representation(
        representation(
            key_chain=ETHEREUM, address="0xC02aaa39", ticker="WETH", native=False, priority=2
        )
    )
    reg.add_representation(
        AssetRepresentation(
            canonical_asset_id="BTC",
            chain_id=0,
            address="0xbtc",
            ticker="BTC",
            decimals=8,
            bridge_issuer=Absence.NOT_APPLICABLE,
            stablecoin_family=Absence.NOT_APPLICABLE,
            pricing_source_priority=0,
            confidence=1.0,
        )
    )
    return reg


def quote(
    venue: str,
    mid: str,
    *,
    second: int = 10,
    key: str | None = None,
    kind: VenueKind = VenueKind.ORDER_BOOK,
) -> VenueQuote:
    return VenueQuote(
        venue_id=venue,
        kind=kind,
        representation_key=key or {"binance": BINANCE_KEY, "okx": OKX_KEY}.get(venue, UNISWAP_KEY),
        mid=Decimal(mid),
        observed_at_ns=at(second),
    )


def executable(
    venue: str,
    *,
    price: str | None,
    cost_bps: float | None,
    notional: str = "100000",
    kind: VenueKind = VenueKind.ORDER_BOOK,
) -> ExecutableQuote:
    return ExecutableQuote(
        venue_id=venue,
        kind=kind,
        notional=Decimal(notional),
        executable_price=None if price is None else Decimal(price),
        all_in_cost_bps=cost_bps,
    )


@pytest.fixture
def three_venues() -> list[VenueQuote]:
    """Mids 2999, 3000, 3010 — median 3000, hand-checkable."""
    return [
        quote("binance", "3000"),
        quote("okx", "2999"),
        quote("uniswap", "3010", kind=VenueKind.AMM_POOL),
    ]
