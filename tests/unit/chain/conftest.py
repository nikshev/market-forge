"""Chain records built by hand (REQ-WP-014)."""

from __future__ import annotations

import pytest

from channelflow.chain import ChainRecord

SECOND_NS = 1_000_000_000
BASE_NS = 1788838800000000000
POOL = "0xPOOL"


def at(second: int) -> int:
    return BASE_NS + second * SECOND_NS


def record(
    *,
    block: int,
    log_index: int = 0,
    block_second: int = 0,
    observed_offset: int = 1,
    available_offset: int = 2,
    block_hash: str | None = None,
    address: str = POOL,
    provider: str = "rpc-a",
) -> ChainRecord:
    return ChainRecord(
        chain_id=1,
        network="ethereum",
        block_number=block,
        block_hash=block_hash or f"0xblock{block}",
        parent_hash=f"0xblock{block - 1}",
        block_time_ns=at(block_second),
        transaction_hash=f"0xtx{block}",
        transaction_index=0,
        log_index=log_index,
        address=address,
        topics=("0xtopic0",),
        data="0xdeadbeef",
        observed_at_ns=at(block_second + observed_offset),
        available_at_ns=at(block_second + available_offset),
        provider=provider,
    )


@pytest.fixture
def three_blocks() -> list[ChainRecord]:
    return [record(block=b, block_second=b) for b in (100, 101, 102)]
