"""Which markets of this deployment are one asset, and the registry that says so.

# @trace: REQ-WP-096

`crossvenue/consensus.py` refuses to compare quotes the registry does not know to be one asset
(PRD §18.13: never merge by ticker). The deployment's markets are listed here, once, with the
asset each stands for and what kind of market it is; the registry the consensus pass hands the
library is built from this list, so the pass and the library cannot disagree about who is
comparable.

**A market representation is identified as a CEX market, not a token**: chain 0 and an address of
the form `cex:<venue>:<symbol>`. The registry's identity is `(chain, address)` (ADR-038); a
venue's market has no contract, and inventing one would be the shortcut the PRD's example
("Hyperliquid ETH market representation") shows is unnecessary.

**Consensus is per market type, never blended** (spec 140, FR-006). Bybit and OKX BTC are both
perpetuals and form one group; Binance's series are spot, and no other spot venue is ingested, so
a spot group has one venue and its consensus is refused -- which is what the Binance panes then
say."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from channelflow.assets import (
    Absence,
    Asset,
    AssetRegistry,
    AssetRepresentation,
    Venue,
    VenueKind,
)


@dataclass(frozen=True)
class ConsensusMarket:
    """One venue's market, and the asset it is a price of."""

    asset_id: str
    venue: str
    symbol: str
    market_type: str


#: The markets the deployment ingests that can enter a consensus. Adding a market is one line here
#: and one stream in `context/sources.py`.
MARKETS: tuple[ConsensusMarket, ...] = (
    ConsensusMarket("BTC", "bybit", "BTCUSDT", "perp"),
    ConsensusMarket("BTC", "okx", "BTC-USDT-SWAP", "perp"),
    ConsensusMarket("BTC", "binance", "BTCUSDT", "spot"),
    ConsensusMarket("ETH", "binance", "ETHUSDT", "spot"),
    ConsensusMarket("SOL", "binance", "SOLUSDT", "spot"),
)


def representation_key(market: ConsensusMarket) -> str:
    """The registry key of a market: chain 0 and a `cex:` address, lower-cased by the registry."""
    return f"0:cex:{market.venue}:{market.symbol}".lower()


def build_registry(markets: tuple[ConsensusMarket, ...] = MARKETS) -> AssetRegistry:
    registry = AssetRegistry()
    for asset_id in sorted({m.asset_id for m in markets}):
        registry.add_asset(Asset(asset_id=asset_id, name=asset_id))
    for venue in sorted({m.venue for m in markets}):
        registry.add_venue(Venue(venue_id=venue, kind=VenueKind.ORDER_BOOK))
    for market in markets:
        registry.add_representation(
            AssetRepresentation(
                canonical_asset_id=market.asset_id,
                chain_id=0,
                address=f"cex:{market.venue}:{market.symbol}",
                ticker=market.symbol,
                decimals=0,
                venue_id=market.venue,
                bridge_issuer=Absence.NOT_APPLICABLE,
                stablecoin_family=Absence.NOT_APPLICABLE,
                pricing_source_priority=0,
                confidence=1.0,
            )
        )
    return registry


def groups(
    markets: tuple[ConsensusMarket, ...] = MARKETS,
) -> dict[tuple[str, str], tuple[ConsensusMarket, ...]]:
    """Markets that are one asset of one market type, keyed `(asset_id, market_type)`."""
    grouped: dict[tuple[str, str], list[ConsensusMarket]] = defaultdict(list)
    for market in markets:
        grouped[(market.asset_id, market.market_type)].append(market)
    return {
        key: tuple(sorted(items, key=lambda m: (m.venue, m.symbol)))
        for key, items in grouped.items()
    }
