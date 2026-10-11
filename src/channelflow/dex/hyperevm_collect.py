"""The DEX collector: HyperEVM logs to stored swaps, and a reading of each pool every poll
(REQ-WP-099).

# @trace: REQ-WP-099

Two jobs, one loop, and nothing it decides is hidden in the node client:

**Swaps, without losing or doubling one.** The cursor is the last block whose swaps are stored. Each
poll asks for `(cursor, safe head]` -- the head minus one block, the chain's finality depth -- in
pieces the node allows, advances the cursor one piece at a time, and **stops at the first piece that
fails**, so the next poll asks for the same blocks. A restart is handed the last stored block as its
cursor. A log from a block at or below the cursor is dropped: the node returning a block twice must
not store it twice. A first run with no history starts a fixed distance behind the head rather than
at the beginning of the chain.

**A reading of every pool, only when the swaps are caught up.** Each poll that reaches the safe head
also reads every pool's liquidity, price and fee at the head and stores one `dex_state` row per
pool, dated at the poll. Those rows are what the worker reads two things from: the active liquidity,
and **that the collector was listening** -- a window with no swap is a quiet market only if the
collector was there to see it ([[REQ-WP-094]] says the same of a quiet liquidation stream). So the
reading is not stored while the swaps are behind, and not for one pool without the other.

**Availability is the poll, not the block.** A swap's event time is its block's; its ingest time is
the poll that stored it. A feature at a close counts only what was stored by then.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from channelflow.chain.hyperevm import SWAP_TOPIC0, RegisteredPool, decode_swap_log
from channelflow.connectors.hyperevm.rpc import (
    MAX_BLOCK_RANGE,
    PoolReading,
    RpcFailure,
    RpcRateLimited,
)
from channelflow.context.status import Status
from channelflow.dex import hyperevm_pools as registry
from channelflow.domain import ChainMeta, DexSwapEvent, EventMeta
from channelflow.tables import dex_state

logger = logging.getLogger(__name__)

SECOND_NS = 1_000_000_000

#: A swap is stored once its block is this many behind the head. HyperEVM finalises in one block
#: (`profiles.HYPEREVM`), so this is the chain's own number and not a margin.
FINALITY_DEPTH = 1

#: How far behind the safe head a collector with no history starts: five minutes of one-second
# blocks, : enough for the first window the pane draws.
START_LOOKBACK_BLOCKS = 300

#: How often the node is asked, and the most pieces one poll may ask for after a long outage: the
#: node rate limits within seconds of a burst, so a catch-up is spread over polls.
POLL_INTERVAL_S = 30
MAX_PIECES_PER_POLL = 5

FLUSH_INTERVAL_S = 300
FLUSH_ROWS = 200

SOURCE = "hyperevm-rpc"


class UnknownPool(LookupError):
    """A log from an address the registry does not name.

    Refused rather than decoded as the family it resembles: the same payload shape belongs to
    different protocols on this chain, and the address is the only thing that says which.
    """


def _hex(log: dict[str, Any], field_name: str) -> int:
    try:
        return int(log[field_name], 16)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"the log has no usable {field_name}") from exc


def price_of(sqrt_price_x96: int, pool: RegisteredPool) -> Decimal:
    """Token1 per token0, in whole tokens, from a square-root price."""
    ratio = Decimal(sqrt_price_x96) / Decimal(2**96)
    scale = Decimal(10) ** (registry.DECIMALS[pool.token0] - registry.DECIMALS[pool.token1])
    return ratio * ratio * scale


def swap_from_log(log: dict[str, Any], *, ingest_time_ns: int) -> DexSwapEvent:
    """One `eth_getLogs` entry as a `DexSwapEvent`."""
    if log.get("removed"):
        raise ValueError("a removed log is a reorganised block's, not a swap")
    pool = registry.BY_ADDRESS.get(str(log.get("address", "")).lower())
    if pool is None:
        raise UnknownPool(f"{log.get('address')} is not a registered HyperEVM pool")
    topics = list(log.get("topics", []))
    if not topics or topics[0] != SWAP_TOPIC0:
        raise ValueError(f"{topics[0] if topics else 'no topic'} is not a swap")
    if "blockTimestamp" not in log:
        # The node did not date the block. Our clock is not the chain's, and a swap dated by it
        # would be a look-ahead the day the two disagree.
        raise ValueError("the log carries no blockTimestamp; refusing to date it by our own clock")
    decoded = decode_swap_log(topics=topics, data=log["data"], address=pool.address, pool=pool)
    block_time_ns = _hex(log, "blockTimestamp") * SECOND_NS
    d0, d1 = registry.DECIMALS[pool.token0], registry.DECIMALS[pool.token1]
    return DexSwapEvent(
        meta=EventMeta(
            source=SOURCE,
            venue=registry.VENUE,
            market_type="dex",
            symbol=pool.address,
            event_time_ns=block_time_ns,
            ingest_time_ns=ingest_time_ns,
            source_event_id=f"{log.get('transactionHash')}:{_hex(log, 'logIndex')}",
        ),
        chain=ChainMeta(
            chain_id=registry.CHAIN_ID,
            block_number=_hex(log, "blockNumber"),
            block_time_ns=block_time_ns,
            tx_hash=str(log["transactionHash"]),
            tx_index=_hex(log, "transactionIndex"),
            log_index=_hex(log, "logIndex"),
        ),
        dex=pool.family.value,
        pool=pool.address,
        token0=pool.token0,
        token1=pool.token1,
        amount0=Decimal(decoded.amount0) / Decimal(10**d0),
        amount1=Decimal(decoded.amount1) / Decimal(10**d1),
        price_token1_per_token0=price_of(decoded.sqrt_price_x96, pool),
        sqrt_price_x96=decoded.sqrt_price_x96,
        tick=decoded.tick,
        liquidity=decoded.liquidity,
    )


class Node(Protocol):
    def head(self) -> int: ...

    def logs(
        self, *, from_block: int, to_block: int, addresses: list[str], topic0: str
    ) -> list[dict[str, Any]]: ...

    def pool_reading(self, pool: RegisteredPool, *, block: int) -> PoolReading: ...


class Sink(Protocol):
    def extend(self, items: Any) -> None: ...

    @property
    def pending(self) -> int: ...

    def flush(self) -> str | None: ...


@dataclass
class DexCollector:
    node: Node
    swaps: Sink
    states: Sink
    status: Status
    now_ns: Callable[[], int]
    #: The last block whose swaps are stored; `None` on a first run with no history.
    cursor: int | None = None
    poll_interval_s: int = POLL_INTERVAL_S
    flush_interval_s: int = FLUSH_INTERVAL_S
    flush_rows: int = FLUSH_ROWS
    _next_poll_ns: int = 0
    _last_flush_ns: int | None = None
    _pools: tuple[RegisteredPool, ...] = field(default=registry.POOLS)

    def step(self) -> None:
        now = self.now_ns()
        if self._last_flush_ns is None:
            self._last_flush_ns = now
        if now >= self._next_poll_ns:
            self._poll(now)
        self._maybe_flush(now)

    # --- one poll ------------------------------------------------------------------------------

    def _poll(self, now: int) -> None:
        regular = now + self.poll_interval_s * SECOND_NS
        self._next_poll_ns = regular
        try:
            head = self.node.head()
            safe = head - FINALITY_DEPTH
            caught_up = self._catch_up(safe, now)
            if caught_up:
                self._read_pools(head, now)
        except RpcRateLimited as exc:
            self._failed(exc)
            self._next_poll_ns = max(regular, now + int(exc.retry_after_s * SECOND_NS))
            return
        except RpcFailure as exc:
            self._failed(exc)
            return
        self.status.record_success()

    def _catch_up(self, safe: int, now: int) -> bool:
        """Store the swaps of `(cursor, safe]`; whether the cursor reached `safe`."""
        if self.cursor is None:
            self.cursor = safe - START_LOOKBACK_BLOCKS
        pieces = 0
        while self.cursor < safe:
            if pieces == MAX_PIECES_PER_POLL:
                return False
            start = self.cursor + 1
            end = min(safe, start + MAX_BLOCK_RANGE - 1)
            logs = self.node.logs(
                from_block=start,
                to_block=end,
                addresses=[pool.address for pool in self._pools],
                topic0=SWAP_TOPIC0,
            )
            self.swaps.extend(self._swaps_of(logs, start=start, ingest_time_ns=now))
            self.cursor = end
            pieces += 1
        return True

    def _swaps_of(
        self, logs: Sequence[dict[str, Any]], *, start: int, ingest_time_ns: int
    ) -> list[DexSwapEvent]:
        swaps = []
        for log in logs:
            # A block at or below the cursor is already stored; the node returning it again is not a
            # second swap.
            if _hex(log, "blockNumber") < start:
                continue
            try:
                swaps.append(swap_from_log(log, ingest_time_ns=ingest_time_ns))
            except (ValueError, UnknownPool) as exc:
                # A log that cannot be read is counted and said, and the rest of the piece is kept:
                # one poison log must not stop the collection for ever, as one bad frame must not
                # stop a stream.
                logger.warning("hyperevm: a log was refused: %s", exc)
                self.status.record_failure("log")
        return swaps

    def _read_pools(self, head: int, now: int) -> None:
        """One row per pool, or none: a heartbeat saying every pool was seen is not half of one."""
        rows = []
        for pool in self._pools:
            reading = self.node.pool_reading(pool, block=head)
            rows.append(
                dex_state.reading_row(
                    chain_id=registry.CHAIN_ID,
                    venue=registry.VENUE,
                    protocol=pool.family.value,
                    pool=pool.address,
                    state_time_ns=now,
                    reference_price=price_of(reading.sqrt_price_x96, pool),
                    active_liquidity=reading.active_liquidity,
                    fee_state=reading.fee_state,
                    block=head,
                )
            )
        self.states.extend(rows)

    def _failed(self, exc: RpcFailure) -> None:
        logger.warning("hyperevm: %s", exc)
        self.status.record_failure(exc.endpoint[:80])

    # --- committing ----------------------------------------------------------------------------

    def _maybe_flush(self, now: int) -> None:
        pending = self.swaps.pending + self.states.pending
        due = (
            self._last_flush_ns is not None
            and now - self._last_flush_ns >= self.flush_interval_s * SECOND_NS
        )
        if due or pending >= self.flush_rows:
            self._flush(now)

    def _flush(self, now: int) -> None:
        failed = False
        for sink in (self.swaps, self.states):
            try:
                sink.flush()
            except Exception as exc:  # noqa: BLE001 -- a failed commit must not stop the collector
                logger.error("hyperevm: could not commit: %s: %s", type(exc).__name__, exc)
                self.status.record_flush_failure()
                failed = True
        if not failed:
            self._last_flush_ns = now

    def close(self) -> None:
        self._flush(self.now_ns())

    def run(self, stop: threading.Event, *, tick_s: float = 1.0) -> None:
        try:
            while not stop.is_set():
                self.step()
                stop.wait(tick_s)
        finally:
            self.close()
