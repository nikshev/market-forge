"""HyperEVM's public JSON-RPC node, as the DEX collector asks it (REQ-WP-099).

# @trace: REQ-WP-099

`ChainDataProvider` (PRD §18.17) is the protocol and, until now, nothing implemented it. This is the
smallest honest implementation of the three reads the collector needs -- the head, the swap logs of
some pools over a block range, and a pool's present state -- over one node.

Every way a request goes wrong is an exception the caller can name, and none is an empty answer: a
collector that read a rate limit as "no swaps" would store a quiet minute that was not one. Two
things about this node were measured on 2026-10-11 and are why it is not a generic client:

* it answers a rate limit as **HTTP 200** with `{"error": {"code": -32005}}` in the body, within
  seconds of a burst, so the body is read before the status is trusted;
* it refuses `eth_getLogs` over more than 1000 blocks, so a wider range is refused here, before it
  is sent, rather than costing a request that is known to fail.

Nothing retries: the loop decides when the next attempt is, because it knows the cadence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from channelflow.chain.hyperevm import PoolFamily, RegisteredPool

#: The node's own limit on `eth_getLogs`, inclusive of both ends.
MAX_BLOCK_RANGE = 1000

#: JSON-RPC's code for "limit exceeded", which this node uses for its rate limit.
RATE_LIMITED_CODE = -32005

#: Used when a rate limit does not say how long to wait: the poll cadence's order of magnitude.
DEFAULT_RETRY_AFTER_S = 30.0

#: `liquidity()`, shared by Uniswap v3 and Algebra.
LIQUIDITY_SELECTOR = "0x1a686502"
#: `slot0()` (Uniswap v3) and `globalState()` (Algebra Integral): the first word is `sqrtPriceX96`
#: and the second the tick on both; Algebra's third is the fee the plugin last published.
SLOT0_SELECTOR = "0x3850c7bd"
GLOBAL_STATE_SELECTOR = "0xe76c01e4"

WORD_HEX = 64


class RpcFailure(Exception):
    """A request that produced no usable answer. `endpoint` names it; `reason` says why."""

    def __init__(self, endpoint: str, reason: str) -> None:
        super().__init__(f"{endpoint}: {reason}")
        self.endpoint = endpoint
        self.reason = reason


class RpcRateLimited(RpcFailure):
    """The node asked us to slow down, and how long to wait."""

    def __init__(self, endpoint: str, retry_after_s: float = DEFAULT_RETRY_AFTER_S) -> None:
        super().__init__(endpoint, f"rate limited, retry after {retry_after_s:g}s")
        self.retry_after_s = retry_after_s


class JsonRpcClient:
    """One node's JSON-RPC over HTTP POST, with a timeout and no retry."""

    def __init__(
        self, url: str, *, timeout: float = 10.0, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.url = url
        self._client = httpx.Client(timeout=timeout, transport=transport)
        self._next_id = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        try:
            response = self._client.post(self.url, json=request)
        except httpx.HTTPError as exc:
            raise RpcFailure(method, f"{type(exc).__name__}: {exc}") from exc
        if response.status_code == 429:
            raise RpcRateLimited(method, _retry_after(response))
        if response.status_code != 200:
            raise RpcFailure(method, f"HTTP {response.status_code}")
        try:
            body = response.json()
        except ValueError as exc:
            raise RpcFailure(method, "the answer is not JSON") from exc
        if not isinstance(body, dict):
            raise RpcFailure(method, "the answer is not a JSON-RPC object")
        error = body.get("error")
        if error is not None:
            code = error.get("code") if isinstance(error, dict) else None
            if code == RATE_LIMITED_CODE:
                raise RpcRateLimited(method)
            message = error.get("message") if isinstance(error, dict) else error
            raise RpcFailure(method, f"error {code}: {message}")
        if "result" not in body:
            raise RpcFailure(method, "the answer has no result")
        return body["result"]

    def close(self) -> None:
        self._client.close()


def _retry_after(response: httpx.Response) -> float:
    try:
        return max(float(response.headers["Retry-After"]), 0.0)
    except (KeyError, ValueError):
        return DEFAULT_RETRY_AFTER_S


@dataclass(frozen=True)
class PoolReading:
    """What one pool reports now: enough to date a liquidity figure and price it."""

    active_liquidity: int
    sqrt_price_x96: int
    tick: int
    #: The pool's fee, in pips, as it reports it: immutable on Uniswap v3, the last published one on
    #: Algebra.
    fee_state: int


def _word(data: str, index: int, *, endpoint: str) -> int:
    body = data.removeprefix("0x")
    chunk = body[index * WORD_HEX : (index + 1) * WORD_HEX]
    if len(chunk) != WORD_HEX:
        raise RpcFailure(endpoint, f"the answer is {len(body) // 2} bytes; word {index} is missing")
    return int(chunk, 16)


def _signed(value: int) -> int:
    return value - (1 << 256) if value >= 1 << 255 else value


class HyperEvmNode:
    """The three reads, over one node."""

    def __init__(self, rpc: JsonRpcClient) -> None:
        self._rpc = rpc

    def head(self) -> int:
        result = self._rpc.call("eth_blockNumber", [])
        try:
            return int(result, 16)
        except (TypeError, ValueError) as exc:
            raise RpcFailure("eth_blockNumber", f"not a block number: {result!r}") from exc

    def logs(
        self, *, from_block: int, to_block: int, addresses: Sequence[str], topic0: str
    ) -> list[dict[str, Any]]:
        if to_block - from_block + 1 > MAX_BLOCK_RANGE:
            raise ValueError(
                f"blocks {from_block}-{to_block} span more than the node's {MAX_BLOCK_RANGE}; "
                "ask in pieces"
            )
        result = self._rpc.call(
            "eth_getLogs",
            [
                {
                    "fromBlock": hex(from_block),
                    "toBlock": hex(to_block),
                    "address": list(addresses),
                    "topics": [topic0],
                }
            ],
        )
        if not isinstance(result, list):
            raise RpcFailure("eth_getLogs", "the answer is not a list of logs")
        return [dict(entry) for entry in result]

    def _call(self, pool: str, selector: str, block: int) -> str:
        result = self._rpc.call("eth_call", [{"to": pool, "data": selector}, hex(block)])
        if not isinstance(result, str):
            raise RpcFailure("eth_call", f"the answer is not hex: {result!r}")
        return result

    def pool_reading(self, pool: RegisteredPool, *, block: int) -> PoolReading:
        """The pool's liquidity, price, tick and fee as of `block`."""
        liquidity = _word(
            self._call(pool.address, LIQUIDITY_SELECTOR, block), 0, endpoint="liquidity"
        )
        algebra = pool.family == PoolFamily.ALGEBRA_INTEGRAL
        state = self._call(
            pool.address, GLOBAL_STATE_SELECTOR if algebra else SLOT0_SELECTOR, block
        )
        endpoint = "globalState" if algebra else "slot0"
        fee = _word(state, 2, endpoint=endpoint) if algebra else pool.fee_pips
        if fee is None:
            raise RpcFailure(endpoint, f"{pool.address} has no fee to report")
        return PoolReading(
            active_liquidity=liquidity,
            sqrt_price_x96=_word(state, 0, endpoint=endpoint),
            tick=_signed(_word(state, 1, endpoint=endpoint)),
            fee_state=fee,
        )
