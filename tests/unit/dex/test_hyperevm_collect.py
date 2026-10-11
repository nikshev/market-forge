"""The DEX collector: chain logs to stored swaps, without losing or doubling one (REQ-WP-099)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from channelflow.connectors.hyperevm.rpc import PoolReading, RpcFailure, RpcRateLimited
from channelflow.context.status import Status
from channelflow.dex import hyperevm_pools as registry
from channelflow.dex.hyperevm_collect import (
    FINALITY_DEPTH,
    START_LOOKBACK_BLOCKS,
    DexCollector,
    UnknownPool,
    swap_from_log,
)
from channelflow.domain import DexSwapEvent

pytestmark = pytest.mark.trace("REQ-WP-099")

SECOND = 1_000_000_000
FIXTURE = json.loads(
    (Path(__file__).parents[2] / "fixtures" / "dex" / "hyperevm_getlogs.json").read_text()
)
LOGS: list[dict[str, Any]] = FIXTURE["logs"]["result"]
FIRST_BLOCK, LAST_BLOCK = FIXTURE["from_block"], FIXTURE["to_block"]
POOL_A, POOL_B = (pool.address for pool in registry.POOLS)


def signed(word: str) -> int:
    value = int(word, 16)
    return value - (1 << 256) if value >= 1 << 255 else value


def payload(log: dict[str, Any]) -> list[str]:
    body = log["data"][2:]
    return [body[i : i + 64] for i in range(0, len(body), 64)]


# --- the conversion --------------------------------------------------------------------------


def test_every_recorded_log_becomes_a_swap_whose_numbers_are_the_logs_own() -> None:
    swaps = [swap_from_log(log, ingest_time_ns=7) for log in LOGS]

    assert len(swaps) == len(LOGS) == 19
    for log, swap in zip(LOGS, swaps, strict=True):
        words = payload(log)
        assert swap.amount0 == Decimal(signed(words[0])) / Decimal(10**18)
        assert swap.amount1 == Decimal(signed(words[1])) / Decimal(10**6)
        assert swap.sqrt_price_x96 == int(words[2], 16)
        assert swap.liquidity == int(words[3], 16)
        assert swap.tick == signed(words[4])
        assert swap.pool == log["address"]
        assert swap.chain.chain_id == 999
        assert swap.chain.block_number == int(log["blockNumber"], 16)
        assert swap.chain.log_index == int(log["logIndex"], 16)
        assert swap.chain.tx_index == int(log["transactionIndex"], 16)
        assert swap.chain.tx_hash == log["transactionHash"]


def test_the_event_time_is_the_blocks_and_the_ingest_time_is_when_we_stored_it() -> None:
    swap = swap_from_log(LOGS[0], ingest_time_ns=123)

    assert swap.meta.event_time_ns == int(LOGS[0]["blockTimestamp"], 16) * SECOND
    assert swap.chain.block_time_ns == swap.meta.event_time_ns
    assert swap.meta.ingest_time_ns == 123


def test_the_price_is_usdc_per_whype_from_the_square_root_price() -> None:
    swap = swap_from_log(LOGS[0], ingest_time_ns=0)

    sqrt = Decimal(int(payload(LOGS[0])[2], 16)) / Decimal(2**96)
    expected = sqrt * sqrt * Decimal(10) ** (18 - 6)
    assert abs(swap.price_token1_per_token0 - expected) / expected < Decimal("1e-12")
    # The pair is HYPE against a dollar: tens of dollars, not 1e-10 and not 1e10.
    assert Decimal(1) < swap.price_token1_per_token0 < Decimal(1000)


def test_each_swap_names_the_protocol_of_the_pool_that_emitted_it() -> None:
    by_pool = {
        swap.pool: swap.dex for swap in (swap_from_log(log, ingest_time_ns=0) for log in LOGS)
    }

    assert by_pool == {
        pool.address: pool.family.value for pool in registry.POOLS if pool.address in by_pool
    }
    assert len(set(by_pool.values())) == 2


def test_a_log_from_a_pool_the_registry_does_not_name_is_refused() -> None:
    foreign = {**LOGS[0], "address": "0x" + "ab" * 20}

    with pytest.raises(UnknownPool):
        swap_from_log(foreign, ingest_time_ns=0)


def test_a_removed_log_is_refused() -> None:
    with pytest.raises(ValueError, match="removed"):
        swap_from_log({**LOGS[0], "removed": True}, ingest_time_ns=0)


def test_a_log_that_is_not_a_swap_is_refused() -> None:
    other = {**LOGS[0], "topics": ["0x" + "11" * 32, *LOGS[0]["topics"][1:]]}

    with pytest.raises(ValueError, match="swap"):
        swap_from_log(other, ingest_time_ns=0)


def test_a_log_without_a_block_time_is_refused_not_dated_by_our_clock() -> None:
    without = {k: v for k, v in LOGS[0].items() if k != "blockTimestamp"}

    with pytest.raises(ValueError, match="blockTimestamp"):
        swap_from_log(without, ingest_time_ns=5)


# --- the loop --------------------------------------------------------------------------------


@dataclass
class FakeNode:
    head_block: int = LAST_BLOCK + FINALITY_DEPTH
    logs_by_block: list[dict[str, Any]] = field(default_factory=lambda: list(LOGS))
    log_calls: list[tuple[int, int]] = field(default_factory=list)
    reading_calls: list[tuple[str, int]] = field(default_factory=list)
    fail_head: list[Exception] = field(default_factory=list)
    fail_logs: list[Exception] = field(default_factory=list)
    fail_readings: list[Exception] = field(default_factory=list)
    extra_logs: list[dict[str, Any]] = field(default_factory=list)

    def head(self) -> int:
        if self.fail_head:
            raise self.fail_head.pop(0)
        return self.head_block

    def logs(
        self, *, from_block: int, to_block: int, addresses: list[str], topic0: str
    ) -> list[dict[str, Any]]:
        self.log_calls.append((from_block, to_block))
        if self.fail_logs:
            raise self.fail_logs.pop(0)
        every = [*self.logs_by_block, *self.extra_logs]
        return [log for log in every if from_block <= int(log["blockNumber"], 16) <= to_block]

    def pool_reading(self, pool: Any, *, block: int) -> PoolReading:
        self.reading_calls.append((pool.address, block))
        if self.fail_readings:
            raise self.fail_readings.pop(0)
        return PoolReading(
            active_liquidity=10**19 if pool.address == registry.LIQUIDITY_POOL else 10**18,
            sqrt_price_x96=int(payload(LOGS[0])[2], 16),
            tick=-1000,
            fee_state=pool.fee_pips if pool.fee_pips is not None else 1073,
        )


@dataclass
class Sink:
    rows: list[Any] = field(default_factory=list)
    flushed: list[list[Any]] = field(default_factory=list)
    fail_flush: bool = False

    def extend(self, items: Any) -> None:
        self.rows.extend(items)

    @property
    def pending(self) -> int:
        return len(self.rows)

    def flush(self) -> str | None:
        if self.fail_flush:
            raise OSError("minio is down")
        if not self.rows:
            return None
        self.flushed.append(list(self.rows))
        self.rows.clear()
        return "hash"


@dataclass
class Rig:
    node: FakeNode
    swaps: Sink
    states: Sink
    now: list[int]
    collector: DexCollector

    def advance(self, seconds: float) -> None:
        self.now[0] += int(seconds * SECOND)


def rig(*, cursor: int | None = None, node: FakeNode | None = None, **config: Any) -> Rig:
    node = node or FakeNode()
    now = [1_800_000_000 * SECOND]
    swaps, states = Sink(), Sink()
    status = Status(venue="hyperevm", poll_interval_s=30, now_ns=lambda: now[0])
    collector = DexCollector(
        node=node,
        swaps=swaps,
        states=states,
        status=status,
        now_ns=lambda: now[0],
        cursor=cursor,
        **config,
    )
    return Rig(node, swaps, states, now, collector)


def stored_swaps(r: Rig) -> list[DexSwapEvent]:
    return [s for batch in r.swaps.flushed for s in batch] + list(r.swaps.rows)


def test_the_first_poll_with_no_history_starts_a_fixed_distance_behind_the_safe_head() -> None:
    r = rig(node=FakeNode(logs_by_block=[]))
    safe = r.node.head_block - FINALITY_DEPTH

    r.collector.step()

    assert r.node.log_calls[0][0] == safe - START_LOOKBACK_BLOCKS + 1
    assert r.node.log_calls[-1][1] == safe


def test_a_poll_stores_every_swap_up_to_the_safe_head_and_moves_the_cursor_there() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)

    r.collector.step()

    assert len(stored_swaps(r)) == 19
    assert r.collector.cursor == LAST_BLOCK


def test_a_swap_is_stored_with_the_time_of_the_poll_as_its_ingest_time() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)

    r.collector.step()

    assert {s.meta.ingest_time_ns for s in stored_swaps(r)} == {r.now[0]}


def test_the_head_block_itself_is_never_asked_for() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)

    r.collector.step()

    assert max(to for _, to in r.node.log_calls) == r.node.head_block - FINALITY_DEPTH


def test_a_poll_that_is_not_due_asks_nothing() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.collector.step()
    calls = len(r.node.log_calls)

    r.advance(10)
    r.collector.step()

    assert len(r.node.log_calls) == calls


def test_blocks_already_stored_are_never_asked_for_again() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.collector.step()
    r.node.head_block += 40
    r.advance(30)

    r.collector.step()

    assert r.node.log_calls[-1] == (LAST_BLOCK + 1, LAST_BLOCK + 40)
    assert len(stored_swaps(r)) == 19


def test_a_restart_from_the_last_stored_block_does_not_store_a_swap_twice() -> None:
    first = rig(cursor=FIRST_BLOCK - 1)
    first.collector.step()
    last_stored = max(s.chain.block_number for s in stored_swaps(first))

    again = rig(cursor=last_stored)
    again.collector.step()

    assert [s.chain.block_number for s in stored_swaps(again)] == [
        s.chain.block_number for s in stored_swaps(first) if s.chain.block_number > last_stored
    ]


def test_a_log_the_node_returns_from_a_block_already_stored_is_dropped() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.collector.step()
    stale = {**LOGS[0]}
    r.node.extra_logs = []
    r.node.head_block += 5
    r.node.logs = lambda **_: [stale]  # type: ignore[method-assign]
    r.advance(30)

    r.collector.step()

    assert len(stored_swaps(r)) == 19


def test_a_log_that_cannot_be_read_is_counted_and_the_rest_of_the_piece_is_kept() -> None:
    poison = {**LOGS[3], "data": "0x1234"}
    r = rig(cursor=FIRST_BLOCK - 1, node=FakeNode(logs_by_block=[*LOGS[:3], poison, *LOGS[4:]]))

    r.collector.step()

    assert len(stored_swaps(r)) == 18
    assert r.collector.status.failures_total["log"] == 1
    assert r.collector.cursor == LAST_BLOCK


@pytest.mark.parametrize(
    "failure", [RpcFailure("eth_getLogs", "HTTP 500"), RpcRateLimited("eth_getLogs", 30)]
)
def test_a_failed_logs_request_stores_nothing_and_leaves_the_cursor(failure: Exception) -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_logs = [failure]

    r.collector.step()

    assert stored_swaps(r) == []
    assert r.states.rows == []
    assert r.collector.cursor == FIRST_BLOCK - 1
    assert r.collector.status.failures_total


def test_the_next_poll_after_a_failure_asks_for_the_same_blocks() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_logs = [RpcFailure("eth_getLogs", "HTTP 500")]
    r.collector.step()
    r.advance(30)

    r.collector.step()

    assert r.node.log_calls[0] == r.node.log_calls[1]
    assert len(stored_swaps(r)) == 19


def test_a_rate_limit_waits_at_least_as_long_as_the_node_asked() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_logs = [RpcRateLimited("eth_getLogs", 90)]
    r.collector.step()
    calls = len(r.node.log_calls)

    r.advance(60)
    r.collector.step()
    assert len(r.node.log_calls) == calls

    r.advance(31)
    r.collector.step()
    assert len(r.node.log_calls) == calls + 1


def test_a_failed_poll_is_not_a_success_and_a_good_one_is() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_logs = [RpcFailure("eth_getLogs", "HTTP 500")]

    r.collector.step()
    assert 'hyperevm"} -1' in r.collector.status.render_metrics()

    r.advance(30)
    r.collector.step()
    assert 'hyperevm"} -1' not in r.collector.status.render_metrics()


def test_a_failed_head_request_is_a_failed_poll() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_head = [RpcFailure("eth_blockNumber", "timeout")]

    r.collector.step()

    assert r.node.log_calls == []
    assert r.collector.cursor == FIRST_BLOCK - 1


def test_a_gap_wider_than_the_node_allows_is_asked_in_contiguous_pieces() -> None:
    r = rig(cursor=FIRST_BLOCK - 3000, node=FakeNode(logs_by_block=[]))

    r.collector.step()

    calls = r.node.log_calls
    assert len(calls) >= 3
    assert all(to - frm + 1 <= 1000 for frm, to in calls)
    assert calls[0][0] == FIRST_BLOCK - 2999
    assert all(b[0] == a[1] + 1 for a, b in zip(calls, calls[1:], strict=False))


def test_a_piece_that_fails_leaves_the_cursor_where_the_last_good_piece_ended() -> None:
    r = rig(cursor=FIRST_BLOCK - 3000, node=FakeNode(logs_by_block=[]))
    r.node.fail_logs = []
    original = r.node.logs
    seen = {"n": 0}

    def flaky(**kw: Any) -> list[dict[str, Any]]:
        seen["n"] += 1
        if seen["n"] == 2:
            raise RpcFailure("eth_getLogs", "HTTP 502")
        return original(**kw)

    r.node.logs = flaky  # type: ignore[method-assign]

    r.collector.step()

    assert r.collector.cursor == FIRST_BLOCK - 3000 + 1000


def test_a_catch_up_is_spread_over_polls_not_hammered_into_one() -> None:
    r = rig(cursor=FIRST_BLOCK - 20_000, node=FakeNode(logs_by_block=[]))

    r.collector.step()

    assert len(r.node.log_calls) <= 5
    assert r.collector.cursor < LAST_BLOCK


def test_each_caught_up_poll_stores_one_reading_per_pool_dated_at_the_poll() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)

    r.collector.step()

    assert len(r.states.rows) == 2
    assert {row["pool"] for row in r.states.rows} == {POOL_A, POOL_B}
    assert {row["state_time_ns"] for row in r.states.rows} == {r.now[0]}
    assert {row["reconstruction_quality"] for row in r.states.rows} == {"partial_ticks"}
    assert {row["to_block"] for row in r.states.rows} == {r.node.head_block}


def test_a_reading_carries_the_liquidity_the_pool_reported() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)

    r.collector.step()

    by_pool = {row["pool"]: row["active_liquidity"] for row in r.states.rows}
    assert by_pool == {POOL_A: str(10**19), POOL_B: str(10**18)}


def test_no_reading_is_stored_while_the_swaps_are_not_caught_up() -> None:
    r = rig(cursor=FIRST_BLOCK - 20_000, node=FakeNode(logs_by_block=[]))

    r.collector.step()

    assert r.states.rows == []
    assert r.node.reading_calls == []


def test_a_reading_that_fails_is_not_stored_and_the_swaps_still_are() -> None:
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_readings = [RpcFailure("eth_call", "timeout")]

    r.collector.step()

    assert len(stored_swaps(r)) == 19
    assert r.states.rows == []
    assert r.collector.status.failures_total


def test_one_pool_failing_stores_no_reading_for_either() -> None:
    # A heartbeat says "the collector saw every pool this minute"; half of one is not that.
    r = rig(cursor=FIRST_BLOCK - 1)
    r.node.fail_readings = [RpcFailure("eth_call", "x")]

    r.collector.step()

    assert r.states.rows == []


def test_a_poll_with_no_new_block_still_confirms_the_collector_is_listening() -> None:
    r = rig(cursor=LAST_BLOCK)

    r.collector.step()

    assert stored_swaps(r) == []
    assert len(r.states.rows) == 2


def test_buffers_are_committed_on_the_interval_and_a_failed_commit_keeps_its_rows() -> None:
    r = rig(cursor=FIRST_BLOCK - 1, flush_interval_s=60)
    r.collector.step()
    assert r.swaps.flushed == []

    r.advance(61)
    r.swaps.fail_flush = True
    r.collector.step()
    assert r.swaps.pending > 0
    assert r.collector.status.flush_failures >= 1

    r.swaps.fail_flush = False
    r.advance(31)
    r.collector.step()
    assert r.swaps.flushed
