"""The registry itself (PRD section 18.13).

# @trace: REQ-ASSET-001

Every refusal here exists because its absence is silent. A dangling canonical
asset surfaces later as a consensus price over something nobody defined; a
duplicate registration means two sources disagree about one token and the
second quietly wins; an ambiguous ticker lookup returns one of several assets
and the caller cannot tell which.

ADR-038: identity is declared, and a lookup that cannot answer refuses rather
than choosing. Convenience is withheld deliberately -- ticker matching is what
every shortcut reduces to, and it is exactly what section 18.13 forbids.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from channelflow.assets.models import (
    Asset,
    AssetRepresentation,
    MarketPair,
    Venue,
)

#: Wrapped-bridged tokens are two or three hops. Anything approaching this is a
#: malformed registry, and bounding the walk means a broken one fails with a
#: message rather than never returning.
MAX_WRAPPER_DEPTH = 32


class UnknownAsset(LookupError):
    """A representation names a canonical asset that is not registered."""


class DuplicateRepresentation(ValueError):
    """One chain and contract, registered twice.

    Two sources disagree about one token. Letting the second win silently is
    how a registry drifts from the chain without anyone noticing.
    """


class AmbiguousTicker(LookupError):
    """More than one asset uses this ticker (ADR-038)."""


class WrapperCycle(ValueError):
    """A wrapper chain loops, or runs deeper than any real one could.

    A registry error, named rather than hung on. The depth bound is belt and
    braces beside the cycle check: with only the cycle check, removing it makes
    the traversal run for ever, and "no answer" is a far weaker signal than a
    wrong one. A bounded walk always terminates with something a test can read.
    """


class UnknownVenue(LookupError):
    """A representation or pair names a venue that is not registered."""


@dataclass
class AssetRegistry:
    """Assets, their representations, the venues and the pairs."""

    assets: dict[str, Asset] = field(default_factory=dict)
    representations: dict[str, AssetRepresentation] = field(default_factory=dict)
    venues: dict[str, Venue] = field(default_factory=dict)
    pairs: dict[str, MarketPair] = field(default_factory=dict)

    # --- registration ---

    def add_asset(self, asset: Asset) -> Asset:
        self.assets[asset.asset_id] = asset
        return asset

    def add_venue(self, venue: Venue) -> Venue:
        self.venues[venue.venue_id] = venue
        return venue

    def add_representation(self, representation: AssetRepresentation) -> AssetRepresentation:
        if representation.canonical_asset_id not in self.assets:
            # Refused at registration rather than at read time: a dangling
            # reference would otherwise surface as a consensus price over an
            # asset nobody defined.
            raise UnknownAsset(
                f"representation {representation.ticker!r} declares canonical asset "
                f"{representation.canonical_asset_id!r}, which is not registered"
            )
        if representation.key in self.representations:
            existing = self.representations[representation.key]
            raise DuplicateRepresentation(
                f"{representation.key} is already registered as {existing.ticker!r}; "
                "one chain and contract identify one token, so a repeat means two "
                "sources disagree about it"
            )
        if representation.venue_id is not None and representation.venue_id not in self.venues:
            raise UnknownVenue(
                f"representation {representation.ticker!r} names venue "
                f"{representation.venue_id!r}, which is not registered"
            )
        self.representations[representation.key] = representation
        return representation

    def add_pair(self, pair: MarketPair) -> MarketPair:
        for side, key in (("base", pair.base_key), ("quote", pair.quote_key)):
            if key not in self.representations:
                raise UnknownAsset(
                    f"pair {pair.pair_id!r} names {side} representation {key!r}, "
                    "which is not registered"
                )
        if pair.venue_id not in self.venues:
            raise UnknownVenue(
                f"pair {pair.pair_id!r} names venue {pair.venue_id!r}, which is not registered"
            )
        self.pairs[pair.pair_id] = pair
        return pair

    # --- resolution ---

    def canonical_asset(self, key: str) -> Asset:
        """The economic asset a representation stands for."""
        representation = self.representations.get(key)
        if representation is None:
            raise UnknownAsset(f"no representation {key!r}")
        return self.assets[representation.canonical_asset_id]

    def same_asset(self, left: str, right: str) -> bool:
        """Whether two representations are the same economic thing.

        By declaration only. Two tokens sharing a ticker are the same asset
        here exactly when someone said so -- section 18.13's prohibition, made
        into the only code path.
        """
        return self.canonical_asset(left).asset_id == self.canonical_asset(right).asset_id

    def representations_of(self, asset_id: str) -> list[AssetRepresentation]:
        """Every representation of an asset, best pricing source first.

        Ordered by priority then by key, so the ordering is total and stable --
        two registries built from the same data list them the same way.
        """
        found = [r for r in self.representations.values() if r.canonical_asset_id == asset_id]
        return sorted(found, key=lambda r: (r.pricing_source_priority, r.key))

    def by_ticker(self, ticker: str) -> Asset:
        """Resolve a ticker, or refuse (ADR-038).

        Works only where exactly one asset uses the ticker, which on a real
        registry is rarely. Returning the first, the most confident or the most
        recently registered would be merging by ticker with extra steps.
        """
        matched = {
            r.canonical_asset_id
            for r in self.representations.values()
            if r.ticker.upper() == ticker.upper()
        }
        if not matched:
            raise UnknownAsset(f"no representation uses ticker {ticker!r}")
        if len(matched) > 1:
            raise AmbiguousTicker(
                f"ticker {ticker!r} is used by {len(matched)} assets "
                f"({', '.join(sorted(matched))}); PRD section 18.13 forbids merging "
                "them, so name the one you mean by chain and address"
            )
        return self.assets[next(iter(matched))]

    def root_of(self, key: str) -> AssetRepresentation:
        """Follow the wrapper chain to its root.

        Wrapped-bridged tokens exist, so a wrapper pointing at another wrapper
        is legal. A cycle is a registry error, and naming it beats looping.
        """
        seen: list[str] = []
        current = self.representations.get(key)
        if current is None:
            raise UnknownAsset(f"no representation {key!r}")
        while current.wraps_representation_key is not None:
            if len(seen) >= MAX_WRAPPER_DEPTH:
                raise WrapperCycle(
                    f"wrapper chain from {key!r} exceeded {MAX_WRAPPER_DEPTH} hops; "
                    "no real wrapping is that deep, so the registry is malformed"
                )
            if current.key in seen:
                raise WrapperCycle("wrapper chain loops: " + " -> ".join([*seen, current.key]))
            seen.append(current.key)
            nxt = self.representations.get(current.wraps_representation_key)
            if nxt is None:
                raise UnknownAsset(
                    f"{current.key} wraps {current.wraps_representation_key!r}, "
                    "which is not registered"
                )
            current = nxt
        return current
