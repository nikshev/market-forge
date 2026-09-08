"""PRD section 18.13's own ETH example, registered (REQ-ASSET-001)."""

from __future__ import annotations

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

ETHEREUM = 1
BASE = 8453
HYPERLIQUID = 998


def representation(
    *,
    asset_id: str,
    chain_id: int,
    ticker: str,
    address: str | None = None,
    is_native: bool = False,
    decimals: int = 18,
    wraps: str | None = None,
    bridge_issuer: object = Absence.NOT_APPLICABLE,
    stablecoin_family: object = Absence.NOT_APPLICABLE,
    priority: int = 0,
    confidence: float = 1.0,
    venue_id: str | None = None,
) -> AssetRepresentation:
    return AssetRepresentation(
        canonical_asset_id=asset_id,
        chain_id=chain_id,
        address=address,
        is_native=is_native,
        ticker=ticker,
        decimals=decimals,
        wraps_representation_key=wraps,
        bridge_issuer=bridge_issuer,  # type: ignore[arg-type]
        stablecoin_family=stablecoin_family,  # type: ignore[arg-type]
        pricing_source_priority=priority,
        confidence=confidence,
        venue_id=venue_id,
    )


@pytest.fixture
def eth_registry() -> AssetRegistry:
    """The PRD's example, verbatim:

    ETH
      |-- native ETH Ethereum
      |-- WETH Ethereum
      |-- WETH Base
      +-- Hyperliquid ETH market representation
    """
    registry = AssetRegistry()
    registry.add_asset(Asset(asset_id="ETH", name="Ether"))
    registry.add_venue(
        Venue(
            venue_id="hyperliquid",
            kind=VenueKind.ONCHAIN_CLOB,
            deployment=ProtocolDeploymentRef(
                protocol="hyperliquid", version="1", chain_id=HYPERLIQUID, address="0xHL"
            ),
        )
    )

    registry.add_representation(
        representation(asset_id="ETH", chain_id=ETHEREUM, ticker="ETH", is_native=True, priority=0)
    )
    registry.add_representation(
        representation(
            asset_id="ETH",
            chain_id=ETHEREUM,
            ticker="WETH",
            address="0xC02aaa39",
            wraps=f"{ETHEREUM}:native",
            priority=1,
        )
    )
    registry.add_representation(
        representation(
            asset_id="ETH",
            chain_id=BASE,
            ticker="WETH",
            address="0x4200000006",
            bridge_issuer="base-bridge",
            priority=2,
        )
    )
    registry.add_representation(
        representation(
            asset_id="ETH",
            chain_id=HYPERLIQUID,
            ticker="ETH",
            address="0xHLETH",
            bridge_issuer=Absence.UNKNOWN,
            priority=3,
            venue_id="hyperliquid",
        )
    )
    return registry
