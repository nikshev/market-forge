"""One pipeline, two chains, and the numbers that decide the difference (REQ-WP-052).

Every figure here was measured against the chain itself across three independent
RPC endpoints. The tests hold the profiles to those measurements, because the
same pipeline given the wrong ones is either a minute slow or wrong.
"""

from __future__ import annotations

import pytest

from channelflow.chain.ledger import FinalityPolicy
from channelflow.chain.profiles import (
    ETHEREUM,
    HYPEREVM,
    PROFILES,
    SECOND_NS,
    ChainProfile,
    UnknownChain,
    profile_for,
)
from channelflow.chain.records import Finality


@pytest.mark.trace("REQ-WP-052")
def test_hyperevm_is_its_own_chain_with_its_own_identity() -> None:
    assert HYPEREVM.chain_id == 999
    assert HYPEREVM.network == "hyperevm"
    assert HYPEREVM.chain_id != ETHEREUM.chain_id


@pytest.mark.trace("REQ-WP-052")
def test_the_two_chains_finalise_orders_of_magnitude_apart() -> None:
    """The measurement the profile exists for: 768 seconds against one, from the
    same policy machinery, decided entirely by which numbers it was handed."""
    assert ETHEREUM.seconds_to_finality() == pytest.approx(768.0)
    assert HYPEREVM.seconds_to_finality() == pytest.approx(1.0)
    assert ETHEREUM.seconds_to_finality() / HYPEREVM.seconds_to_finality() > 100


@pytest.mark.trace("REQ-WP-052")
def test_hyperevm_finalises_within_the_block() -> None:
    """`latest`, `safe` and `finalized` were the same block on all three
    endpoints. A depth of one is this pipeline's way of saying "the block
    itself"."""
    assert HYPEREVM.finality.safe_depth == 1
    assert HYPEREVM.finality.finalized_depth == 1
    assert HYPEREVM.block_time_ns == SECOND_NS


@pytest.mark.trace("REQ-WP-052")
def test_ethereum_keeps_the_depths_the_pipeline_was_built_with() -> None:
    """Left alone deliberately. Changing them changes what every existing
    consumer sees, which is a decision with its own evidence to gather."""
    assert ETHEREUM.finality.finalized_depth == 64
    assert ETHEREUM.block_time_ns == 12 * SECOND_NS


@pytest.mark.trace("REQ-WP-052")
def test_the_same_confirmation_count_means_different_things_on_the_two_chains() -> None:
    """Which is the whole argument for a profile rather than a default.

    Five confirmations is final on one chain and barely seen on the other, and
    nothing about the number says which chain it belongs to.
    """
    assert HYPEREVM.finality.status_for(5) is Finality.FINALIZED
    assert ETHEREUM.finality.status_for(5) is Finality.HEAD_CONFIRMED


@pytest.mark.trace("REQ-WP-052")
def test_a_chain_nobody_measured_is_refused() -> None:
    """A confirmation depth borrowed from another chain is not a confirmation
    depth. Base, here, which this project reads from elsewhere and has never
    measured finality on."""
    assert profile_for(1) is ETHEREUM
    assert profile_for(999) is HYPEREVM
    with pytest.raises(UnknownChain, match="no measured profile"):
        profile_for(8453)


@pytest.mark.trace("REQ-WP-052")
@pytest.mark.parametrize(
    "profile", list(PROFILES.values()), ids=[p.network for p in PROFILES.values()]
)
def test_every_profile_names_more_than_one_endpoint(profile: ChainProfile) -> None:
    """§18.17's multi-provider strategy: a value one endpoint alone reports is a
    value nobody has checked."""
    assert len(profile.rpcs) >= 2
    assert len(set(profile.rpcs)) == len(profile.rpcs)


@pytest.mark.trace("REQ-WP-052")
def test_a_profile_with_one_endpoint_is_refused() -> None:
    with pytest.raises(ValueError, match="multi-provider"):
        ChainProfile(
            chain_id=5,
            network="lonely",
            block_time_ns=SECOND_NS,
            finality=FinalityPolicy(),
            rpcs=("https://only-one",),
        )


@pytest.mark.trace("REQ-WP-052")
def test_a_profile_without_a_chain_id_is_refused() -> None:
    with pytest.raises(ValueError, match="names no chain"):
        ChainProfile(
            chain_id=0,
            network="nameless",
            block_time_ns=SECOND_NS,
            finality=FinalityPolicy(),
            rpcs=("https://a", "https://b"),
        )
