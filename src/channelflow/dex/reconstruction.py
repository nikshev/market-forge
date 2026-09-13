"""PRD §18.12.2's `reconstruction_quality`: what a rebuilt state knows about itself.

# @trace: REQ-WP-060

§18.12.2 ends `LiquidityState` with a field nothing produced, and §18.24 asks
for it as a method — `def quality(self, state) -> ReconstructionQuality`.
[[REQ-WP-015]] already rebuilds the state correctly. This is the part that says
how much of it is real.

**Two of the state's parts behave completely differently under a partial
replay.** A `Swap` reports the `liquidity` the pool had, so active liquidity
self-heals at the first swap of any window. The tick map accumulates only the
mints and burns the window saw, and never self-heals — a range initialised
before the window is simply absent.

Measured on Ethereum's deepest USDC/WETH pool, replaying its last 100 blocks
(`tests/fixtures/pool_state/`): active liquidity 5481181047667912297 and current
tick 197999, **both exactly the contract's own**, with a tick map containing
nothing at all. §18.7.1's traversal over that map then reports that fifty basis
points is unreachable with zero notional, for the deepest pool on the chain.
[[REQ-WP-059]] draws that as a band saying "exhausted at 0 bps".

**§18.7.2's recovery check does not catch it, and cannot.** It compares the
three scalars a swap already reports; on that state two matched exactly and the
third differed by 1.4e-8 relative — under a thousandth of a basis point of price,
being drift over the blocks between the last swap and the read. A reader would
read that as noise, correctly, and the empty tick map is invisible to it because
it never looks there.

**So the detection used here is the pool's own arithmetic, not a claim.** In a
concentrated-liquidity pool the liquidity at the current tick is the running sum
of `liquidity_net` over every initialised tick at or below it. A complete map
therefore satisfies

    sum(liquidity_net for tick <= current_tick) == active_liquidity

and the two sides come from different events — mints and burns on the left, the
swap's own report on the right. A disagreement proves the map is incomplete
without an archive node, a checkpoint or anybody's assertion. Equality does not
strictly prove completeness, since errors could cancel, and that is said here
rather than implied.

**Contiguity is the one thing that must be asserted.** A block with no `Mint` is
indistinguishable from a block whose `Mint` was not fetched, so whether the
replayed range has holes is known only to whoever read the chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from channelflow.dex.pool import IntegrityIncident, PoolState


class ReconstructionQuality(StrEnum):
    """What a reconstructed state may be used for.

    Derived, not quoted: §18.12.2 names the field and never enumerates it. Each
    value is a statement about use rather than a grade.
    """

    #: The tick map accounts for the active liquidity, and a contract read taken
    #: at the state's own block agreed.
    ANCHORED = "anchored"
    #: The tick map accounts for the active liquidity. Not reconciled, or
    #: reconciled against a different block, which is not evidence.
    REPLAYED = "replayed"
    #: It does not. Scalars may be exact and the depth curve is not the pool's.
    PARTIAL_TICKS = "partial_ticks"
    #: The replayed range has holes, so events are missing whatever the map says.
    GAPPED = "gapped"
    #: A contract read at the state's own block disagreed.
    DIVERGED = "diverged"


#: The classes a §18.7.1 traversal may run over. The other three are the cases
#: where it would answer from a map it cannot vouch for, and a refusal is the
#: only honest output — the rule [[REQ-WP-047]] applies to `CUSTOM_ACCOUNTING`
#: pools, for the same reason.
DEPTH_CAPABLE = frozenset({ReconstructionQuality.ANCHORED, ReconstructionQuality.REPLAYED})


class DepthNotSupported(ValueError):
    """A depth curve was asked of a state that cannot support one."""


@dataclass(frozen=True)
class Provenance:
    """What the reader of the chain asserts about what it replayed.

    `contiguous` cannot be derived from the events, which is why it is a field
    somebody has to fill in rather than something computed here.
    """

    from_block: int
    to_block: int
    contiguous: bool
    #: The block a direct contract read seeded the state from, if any. Recorded
    #: for provenance; completeness is measured rather than inferred from it.
    checkpoint_block: int | None = None

    def __post_init__(self) -> None:
        if self.to_block < self.from_block:
            raise ValueError(f"range {self.from_block}-{self.to_block} runs backwards")


@dataclass(frozen=True)
class Reconciliation:
    """§18.7.2's comparison, and whether it was taken where it means anything.

    A contract read at a later block disagrees with a correct reconstruction
    whenever anything traded in between, so an unaligned comparison is not
    evidence either way. Folding it in as a divergence is how a real check
    becomes noise: the measured case differed by 1.4e-8 relative on one field
    while the state's actual defect was an empty tick map.
    """

    incident: IntegrityIncident
    #: The block the contract was read at.
    read_at_block: int
    #: The last block the replay applied.
    state_block: int

    @property
    def aligned(self) -> bool:
        return self.read_at_block == self.state_block

    @property
    def disagrees(self) -> bool:
        return self.aligned and self.incident.diverged


def implied_active_liquidity(state: PoolState) -> Decimal:
    """What the tick map says the liquidity at the current tick should be."""
    return sum(
        (net for tick, net in state.tick_liquidity_net.items() if tick <= state.current_tick),
        Decimal(0),
    )


def tick_map_accounts_for_liquidity(state: PoolState) -> bool:
    """Whether the map explains the liquidity the pool reported.

    The sufficient test for incompleteness. Not a proof of completeness: two
    errors could cancel, which is unlikely enough to rely on and dishonest to
    call impossible.
    """
    return implied_active_liquidity(state) == state.active_liquidity


def quality(
    state: PoolState,
    *,
    provenance: Provenance,
    reconciliation: Reconciliation | None = None,
) -> ReconstructionQuality:
    """§18.24's `quality`, in the order the failures matter.

    A gap is checked first: it means events are missing whatever the tick map
    happens to add up to, so a map that balances by luck must not outrank it.
    """
    if not provenance.contiguous:
        return ReconstructionQuality.GAPPED
    if not tick_map_accounts_for_liquidity(state):
        return ReconstructionQuality.PARTIAL_TICKS
    if reconciliation is not None and reconciliation.disagrees:
        return ReconstructionQuality.DIVERGED
    if reconciliation is not None and reconciliation.aligned:
        return ReconstructionQuality.ANCHORED
    return ReconstructionQuality.REPLAYED


def require_tick_map_complete(state: PoolState) -> None:
    """Refuse a traversal over a tick map that cannot explain the pool.

    Called from the traversal itself rather than left to a caller: the state
    that fails this is the one that looks most normal, reporting the contract's
    own tick and liquidity, so a check somebody has to remember is a check that
    will be missed.

    **This is everything the traversal can check.** A `PoolState` carries no
    provenance, so a `GAPPED` reconstruction whose surviving events happen to
    balance passes here and is refused by `require_depth_capable` instead. Two
    guards, each where the information it needs exists -- rather than one guard
    that would have to take the other's input on trust.
    """
    if tick_map_accounts_for_liquidity(state):
        return
    raise DepthNotSupported(
        f"the tick map of {state.address} implies liquidity "
        f"{implied_active_liquidity(state)} at tick {state.current_tick} while the pool "
        f"reports {state.active_liquidity}; the map is incomplete, and a curve from it "
        "would report the pool as thinner than it is rather than failing"
    )


def require_depth_capable(quality: ReconstructionQuality) -> None:
    """Refuse a curve from a state whose quality does not permit one.

    The outer gate, for callers that know the provenance. It catches the case
    the traversal cannot see: a gap, which is asserted rather than measured and
    means events are missing however well the rest adds up.
    """
    if quality in DEPTH_CAPABLE:
        return
    raise DepthNotSupported(
        f"a depth curve may not be computed from a {quality} reconstruction; "
        f"permitted: {', '.join(sorted(q.value for q in DEPTH_CAPABLE))}"
    )
