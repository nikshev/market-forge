"""PRD section 18.13's asset registry entities.

# @trace: REQ-ASSET-001

    "Cross-chain/venue comparison is impossible without a strict asset
     registry."

The section's own example is the shape this has to express:

    ETH
      |-- native ETH Ethereum
      |-- WETH Ethereum
      |-- WETH Base
      +-- Hyperliquid ETH market representation

Four representations, one economic asset, and the relationship declared rather
than guessed -- ADR-038. The prohibition that goes with it is one sentence and
easy to violate: "Do not merge wrapped, bridged or synthetic assets only by
ticker."

Two fields are three-state rather than optional (ADR-037). A native asset has
no bridge issuer; a bridged asset whose issuer nobody recorded has an unknown
one. `None` for both would make a provenance filter inexpressible.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Absence(StrEnum):
    """Why a field has no value (ADR-037).

    Not a sentinel dressed as data: a consumer filtering on provenance needs to
    tell "this asset cannot have a bridge issuer" from "nobody wrote down who
    issued this bridge", and those are opposite facts.
    """

    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


#: A value, or a stated reason there is none. Never merely missing.
Optional3 = str | Absence


class VenueKind(StrEnum):
    """What kind of place trading happens in.

    §18.14 compares an order book and an AMM differently, so the registry has
    to say which a venue is -- an AMM's infinitesimal spot quote and a book's
    top of book are not the same object.
    """

    ORDER_BOOK = "order_book"
    AMM_POOL = "amm_pool"
    ONCHAIN_CLOB = "onchain_clob"


class ProtocolDeploymentRef(BaseModel):
    """A named deployment, not a copy of one.

    REQ-WP-014's `RegistryEntry` already models deployments for decoding; this
    references one by protocol, version and address rather than duplicating it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol: str = Field(min_length=1)
    version: str = Field(min_length=1)
    chain_id: int = Field(ge=1)
    address: str = Field(min_length=1)


class Venue(BaseModel):
    """Where a pair trades."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    venue_id: str = Field(min_length=1)
    kind: VenueKind
    deployment: ProtocolDeploymentRef | None = None

    def model_post_init(self, _: object) -> None:
        onchain = self.kind in (VenueKind.AMM_POOL, VenueKind.ONCHAIN_CLOB)
        if onchain and self.deployment is None:
            raise ValueError(
                f"venue {self.venue_id!r} is on-chain and names no protocol "
                "deployment; without it nothing downstream can say which contract "
                "it is quoting"
            )
        if not onchain and self.deployment is not None:
            raise ValueError(
                f"venue {self.venue_id!r} is an order book and names a protocol "
                "deployment; an order book has no contract to deploy"
            )


class Asset(BaseModel):
    """A canonical economic thing, independent of where it is held."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    asset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class AssetRepresentation(BaseModel):
    """One concrete token or market standing for an asset.

    Identity is `(chain_id, address)`, or the native marker (ADR-038). Two
    representations differing in either are distinct, whatever they are called.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    #: Declared, never inferred. A representation without one is refused.
    canonical_asset_id: str = Field(min_length=1)
    chain_id: int = Field(ge=0)
    #: The contract, or `None` together with `is_native=True`.
    address: str | None = None
    is_native: bool = False
    ticker: str = Field(min_length=1)
    decimals: int = Field(ge=0, le=36)
    venue_id: str | None = None

    #: PRD §18.13's wrapper/underlying relationship. `None` means this
    #: representation is a root -- which is a relationship, not an absence.
    wraps_representation_key: str | None = None

    #: Three-state (ADR-037). No default: a representation registered without
    #: stating which is refused by the type.
    bridge_issuer: Optional3
    stablecoin_family: Optional3

    pricing_source_priority: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)

    @property
    def key(self) -> str:
        """The only identification that means anything (ADR-038)."""
        if self.is_native:
            return f"{self.chain_id}:native"
        return f"{self.chain_id}:{(self.address or '').lower()}"

    def model_post_init(self, _: object) -> None:
        if self.is_native and self.address is not None:
            raise ValueError(
                f"{self.ticker} on chain {self.chain_id} is marked native and also "
                "carries a contract address; it is one or the other"
            )
        if not self.is_native and not self.address:
            raise ValueError(
                f"{self.ticker} on chain {self.chain_id} has no contract address and "
                "is not marked native; nothing identifies it"
            )


class MarketPair(BaseModel):
    """Two representations traded against each other somewhere."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pair_id: str = Field(min_length=1)
    base_key: str = Field(min_length=1)
    quote_key: str = Field(min_length=1)
    venue_id: str = Field(min_length=1)

    def model_post_init(self, _: object) -> None:
        if self.base_key == self.quote_key:
            raise ValueError(
                f"pair {self.pair_id!r} has the same representation on both sides; "
                "a market against itself has no price"
            )
