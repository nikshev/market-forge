"""Availability, finality and reorgs (REQ-WP-014, REQ-BIAS-006)."""

from __future__ import annotations

import pytest

from channelflow.chain import (
    ChainLedger,
    ChainRecord,
    Finality,
    FinalityPolicy,
    FinalizedBlockCannotReorg,
)

from .conftest import at, record


@pytest.mark.trace("REQ-WP-014")
def test_a_record_is_invisible_until_it_was_available() -> None:
    """SC-001, FR-002, PRD section 18.19:

        "A historical backtest at 12:00:01.500 must not see that swap even
        though block_time is earlier."

    The block is timed at second 100; the log was only complete at 102.
    """
    ledger = ChainLedger()
    ledger.append(record(block=100, block_second=100, observed_offset=1, available_offset=2))

    assert ledger.as_of(at(101)) == []
    assert len(ledger.as_of(at(102))) == 1


@pytest.mark.trace("REQ-WP-014")
def test_availability_is_never_before_observation() -> None:
    """FR-004, the spec's second edge case."""
    with pytest.raises(ValueError, match="cannot see something before it happened"):
        record(block=100, block_second=100, observed_offset=-5)


@pytest.mark.trace("REQ-WP-014")
def test_a_backtest_cannot_read_earlier_than_the_live_system_could() -> None:
    """FR-004. The ordering the whole section rests on."""
    with pytest.raises(ValueError, match="section 18.19"):
        ChainRecord(
            chain_id=1,
            network="ethereum",
            block_number=1,
            block_hash="0xa",
            parent_hash="0x0",
            block_time_ns=at(10),
            transaction_hash="0xtx",
            transaction_index=0,
            log_index=0,
            address="0xPOOL",
            topics=("0xt",),
            observed_at_ns=at(20),
            available_at_ns=at(15),
            provider="rpc-a",
        )


@pytest.mark.trace("REQ-WP-014")
def test_finality_advances_at_the_configured_depths(
    three_blocks: list[ChainRecord],
) -> None:
    """SC-005, FR-008, PRD section 18.4."""
    ledger = ChainLedger(
        policy=FinalityPolicy(head_confirmed_depth=1, safe_depth=5, finalized_depth=10)
    )
    for r in three_blocks:
        ledger.append(r)

    ledger.advance(head_block=102, at_ns=at(200))
    assert ledger.records[0].finality is Finality.HEAD_CONFIRMED

    ledger.advance(head_block=106, at_ns=at(300))
    assert ledger.records[0].finality is Finality.SAFE

    ledger.advance(head_block=115, at_ns=at(400))
    assert ledger.records[0].finality is Finality.FINALIZED


@pytest.mark.trace("REQ-WP-014")
def test_finality_never_regresses(three_blocks: list[ChainRecord]) -> None:
    """FR-008. A status that could go backwards is not a guarantee anyone can
    act on."""
    ledger = ChainLedger(policy=FinalityPolicy(safe_depth=5, finalized_depth=10))
    for r in three_blocks:
        ledger.append(r)

    ledger.advance(head_block=115, at_ns=at(300))
    assert ledger.records[0].finality is Finality.FINALIZED

    ledger.advance(head_block=100, at_ns=at(400))
    assert ledger.records[0].finality is Finality.FINALIZED


@pytest.mark.trace("REQ-WP-014")
def test_a_safe_only_read_excludes_what_had_not_reached_it(
    three_blocks: list[ChainRecord],
) -> None:
    """SC-002, FR-003, PRD section 18.4 rule 2: "Research datasets default to
    SAFE or stronger"."""
    ledger = ChainLedger(policy=FinalityPolicy(safe_depth=5))
    for r in three_blocks:
        ledger.append(r)
    ledger.advance(head_block=102, at_ns=at(200))

    assert ledger.as_of(at(200)) != []
    assert ledger.as_of(at(200), require=Finality.SAFE) == []

    ledger.advance(head_block=110, at_ns=at(300))
    assert ledger.as_of(at(300), require=Finality.SAFE) != []


@pytest.mark.trace("REQ-WP-014")
@pytest.mark.trace("REQ-BIAS-006")
def test_a_reorg_orphans_a_record_and_never_edits_it() -> None:
    """SC-003, FR-005, FR-006, ADR-033, PRD section 18.4 rule 5:

    "A reorg cannot silently mutate an existing signal snapshot; emit an
    invalidation/correction event instead."
    """
    ledger = ChainLedger()
    original = ledger.append(record(block=100, block_second=100))
    before = original.model_dump()

    invalidation = ledger.reorg(
        chain_id=1,
        block_number=100,
        orphaned_block_hash="0xblock100",
        at_ns=at(500),
        reason="head reorganised",
    )

    stored = ledger.records[0]
    assert stored.orphaned_at_ns == at(500)
    assert {k: v for k, v in stored.model_dump().items() if k != "orphaned_at_ns"} == {
        k: v for k, v in before.items() if k != "orphaned_at_ns"
    }
    assert invalidation.orphaned_block_hash == "0xblock100"


@pytest.mark.trace("REQ-WP-014")
@pytest.mark.trace("REQ-BIAS-006")
def test_a_read_before_the_reorg_still_returns_the_record() -> None:
    """SC-003, ADR-033, PRD section 41 rule 6.

    It was genuinely what was known then. A point-in-time read that hid it
    would be reconstructing history rather than reporting it -- and a backtest
    replayed over corrected data would never make the decision the live system
    made, which looks exactly like the strategy improving.
    """
    ledger = ChainLedger()
    ledger.append(record(block=100, block_second=100))
    ledger.reorg(
        chain_id=1,
        block_number=100,
        orphaned_block_hash="0xblock100",
        at_ns=at(500),
        reason="head reorganised",
    )

    assert len(ledger.as_of(at(300))) == 1, "before the reorg it was real"
    assert ledger.as_of(at(600)) == [], "after it, it is not"


@pytest.mark.trace("REQ-WP-014")
def test_a_finalized_block_cannot_be_reorganised(
    three_blocks: list[ChainRecord],
) -> None:
    """SC-004, FR-007.

    Finality is the claim that this cannot happen. A chain contradicting it is
    a bug or an attack, and either way not something to absorb silently.
    """
    ledger = ChainLedger(policy=FinalityPolicy(finalized_depth=5))
    for r in three_blocks:
        ledger.append(r)
    ledger.advance(head_block=120, at_ns=at(300))

    with pytest.raises(FinalizedBlockCannotReorg, match="cannot be reorganised"):
        ledger.reorg(
            chain_id=1,
            block_number=100,
            orphaned_block_hash="0xblock100",
            at_ns=at(400),
            reason="impossible",
        )


@pytest.mark.trace("REQ-WP-014")
def test_a_reorg_of_an_unseen_block_is_recorded_and_harmless() -> None:
    """The spec's third edge case: the invalidation names a block nothing
    depended on."""
    ledger = ChainLedger()

    invalidation = ledger.reorg(
        chain_id=1,
        block_number=999,
        orphaned_block_hash="0xnever_seen",
        at_ns=at(500),
        reason="observed on another provider",
    )

    assert invalidation in ledger.invalidations
    assert ledger.records == []


@pytest.mark.trace("REQ-WP-014")
def test_records_are_returned_in_chain_order(three_blocks: list[ChainRecord]) -> None:
    """Block, then transaction index, then log index -- the only total order a
    chain gives, and the one a replay must follow."""
    ledger = ChainLedger()
    for r in reversed(three_blocks):
        ledger.append(r)

    visible = ledger.as_of(at(1000))

    assert [r.block_number for r in visible] == [100, 101, 102]


@pytest.mark.trace("REQ-WP-014")
def test_a_record_is_immutable(three_blocks: list[ChainRecord]) -> None:
    """FR-017, PRD section 18.3: "Raw chain records are immutable append-only
    data"."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        three_blocks[0].block_number = 1  # type: ignore[misc]
