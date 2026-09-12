"""What one chain is, so the ingestion pipeline can be pointed at another.

# @trace: REQ-WP-052

PRD section 18.11.2 says HyperEVM's contracts "enter the standard EVM
raw-block/log pipeline" and asks for HyperEVM's block identity to be tracked
separately. [[REQ-WP-014]] built that pipeline against Ethereum, with the
chain's properties as defaults on `FinalityPolicy`.

**Those defaults describe Ethereum, and pointing them at HyperEVM would cost a
minute of latency on every feature.** Measured on 2026-09-12 across three
independent RPC endpoints:

    chain       block time   `safe` lag   `finalized` lag
    -------------------------------------------------------
    Ethereum      ~12s        33 blocks     65 blocks
    HyperEVM        1s         0 blocks      0 blocks

HyperEVM's `latest`, `safe` and `finalized` are the same block: HyperBFT
finalises within the block, and all three endpoints agree. Ethereum's defaults
of 12 and 64 would make this pipeline wait sixty-four seconds to call something
final that the chain finalised a second ago.

**The reverse is what makes a profile necessary rather than convenient.** Carry
HyperEVM's depths onto Ethereum and the pipeline calls a block finalised that
can still reorg — the same number, and one direction is a delay while the other
is wrong data.

A profile is therefore per chain and explicit. There is no default profile, for
the reason there is no default contract value in the OKX connector: the common
case is the dangerous one.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.chain.ledger import FinalityPolicy

SECOND_NS = 1_000_000_000


class UnknownChain(LookupError):
    """No profile for this chain.

    Refused rather than defaulted. A chain nobody has measured has no
    confirmation depth that can be honestly claimed, and borrowing a
    neighbour's is how a block that can reorg gets called final.
    """


@dataclass(frozen=True)
class ChainProfile:
    """One chain's identity and how fast it settles.

    Every field was measured against the chain itself rather than read, and the
    docstring above carries the numbers.
    """

    chain_id: int
    network: str
    #: Measured median, not a documented target.
    block_time_ns: int
    finality: FinalityPolicy
    #: Endpoints that answered without a key. More than one, because
    #: [[REQ-WP-014]]'s provider pool compares them and a value one endpoint
    #: alone reports is a value nobody has checked.
    rpcs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.chain_id < 1:
            raise ValueError(f"{self.network}: a chain id of {self.chain_id} names no chain")
        if len(self.rpcs) < 2:
            raise ValueError(
                f"{self.network}: one endpoint is not a multi-provider strategy (section 18.17)"
            )

    def seconds_to_finality(self) -> float:
        """How long this chain takes to finalise, at its measured block time.

        The figure the profile exists for: sixty-four seconds against one, from
        the same pipeline, decided entirely by which profile it was given.
        """
        return self.finality.finalized_depth * self.block_time_ns / SECOND_NS


#: Ethereum's `safe` and `finalized` tags lagged the head by 33 and 65 blocks.
#:
#: The depths here are [[REQ-WP-014]]'s and are left as they were. Worth noting
#: rather than changing: `safe_depth=12` calls a block safe some twenty blocks
#: before Ethereum's own `safe` tag does, which is a heuristic that predates the
#: tag existing. Changing it would change what every existing consumer of this
#: pipeline sees, and that is a decision with its own evidence to gather.
ETHEREUM = ChainProfile(
    chain_id=1,
    network="ethereum",
    block_time_ns=12 * SECOND_NS,
    finality=FinalityPolicy(head_confirmed_depth=1, safe_depth=12, finalized_depth=64),
    rpcs=(
        "https://ethereum-rpc.publicnode.com",
        "https://eth.drpc.org",
        "https://1rpc.io/eth",
    ),
)

#: HyperEVM reported `latest`, `safe` and `finalized` as the same block on all
#: three endpoints, with one-second blocks. A depth of one is this pipeline's way
#: of saying "the block itself"; it cannot say zero, because a record with no
#: confirmations is one this collector has seen and the chain has not yet agreed
#: to.
HYPEREVM = ChainProfile(
    chain_id=999,
    network="hyperevm",
    block_time_ns=SECOND_NS,
    finality=FinalityPolicy(head_confirmed_depth=1, safe_depth=1, finalized_depth=1),
    rpcs=(
        "https://rpc.hyperliquid.xyz/evm",
        "https://rpc.hypurrscan.io",
        "https://hyperliquid.drpc.org",
    ),
)

PROFILES: dict[int, ChainProfile] = {profile.chain_id: profile for profile in (ETHEREUM, HYPEREVM)}


def profile_for(chain_id: int) -> ChainProfile:
    """The profile for a chain, or a refusal.

    Never a fallback. Two chains' depths are the same numbers meaning opposite
    things, and picking one for a chain nobody measured is how a reorgable block
    gets called final.
    """
    if chain_id not in PROFILES:
        raise UnknownChain(
            f"chain {chain_id} has no measured profile; a confirmation depth "
            "borrowed from another chain is not a confirmation depth"
        )
    return PROFILES[chain_id]
