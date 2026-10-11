"""HyperEVM's public node, as the collector asks it (REQ-WP-099).

Every way a request can go wrong is an exception the caller can name, and none of them is an
empty answer: a collector that read "the node failed" as "no swaps" would store a quiet minute
that was a rate limit.
"""

from __future__ import annotations

import json

import httpx
import pytest

from channelflow.connectors.hyperevm.rpc import (
    MAX_BLOCK_RANGE,
    HyperEvmNode,
    JsonRpcClient,
    RpcFailure,
    RpcRateLimited,
)

pytestmark = pytest.mark.trace("REQ-WP-099")

POOL_A = "0x6c9a33e3b592c0d65b3ba59355d5be0d38259285"
POOL_B = "0xbe512f5881b85c48d9c17bc5bb2be047d156d696"
SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"


def client_for(handler: object) -> JsonRpcClient:
    return JsonRpcClient("http://node.invalid/evm", transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def answering(result: object, seen: list[dict[str, object]] | None = None) -> object:
    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if seen is not None:
            seen.append(body)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    return handle


def test_a_call_posts_a_json_rpc_request_and_returns_the_result() -> None:
    seen: list[dict[str, object]] = []
    client = client_for(answering("0x2e07464", seen))

    assert client.call("eth_blockNumber", []) == "0x2e07464"
    assert seen[0]["method"] == "eth_blockNumber"
    assert seen[0]["params"] == []
    assert seen[0]["jsonrpc"] == "2.0"


def test_a_rate_limit_inside_a_200_answer_is_a_rate_limit() -> None:
    # The node answers HTTP 200 with the limit in the body -- measured 2026-10-11.
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32005, "message": "rate limited"},
            },
        )

    with pytest.raises(RpcRateLimited) as raised:
        client_for(handle).call("eth_getLogs", [{}])

    assert raised.value.retry_after_s > 0


def test_http_429_is_a_rate_limit_and_honours_retry_after() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "7"})

    with pytest.raises(RpcRateLimited) as raised:
        client_for(handle).call("eth_blockNumber", [])

    assert raised.value.retry_after_s == 7


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(503, json={"jsonrpc": "2.0", "id": 1, "result": "0x1"}),
        httpx.Response(200, content=b"<html>bad gateway</html>"),
        httpx.Response(200, json={"jsonrpc": "2.0", "id": 1}),
        httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad params"}},
        ),
    ],
    ids=["http-500", "http-503-with-a-result", "not-json", "no-result", "error-object"],
)
def test_every_other_failure_is_an_rpc_failure_that_is_not_a_rate_limit(
    response: httpx.Response,
) -> None:
    with pytest.raises(RpcFailure) as raised:
        client_for(lambda request: response).call("eth_blockNumber", [])

    assert not isinstance(raised.value, RpcRateLimited)


def test_a_transport_error_is_an_rpc_failure() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    with pytest.raises(RpcFailure):
        client_for(handle).call("eth_blockNumber", [])


def test_the_head_is_the_hex_block_number_as_an_int() -> None:
    assert HyperEvmNode(client_for(answering("0x2e07464"))).head() == 0x2E07464


def test_logs_ask_for_both_pools_and_the_swap_topic_over_an_inclusive_range() -> None:
    seen: list[dict[str, object]] = []
    node = HyperEvmNode(client_for(answering([], seen)))

    assert (
        node.logs(from_block=100, to_block=1099, addresses=[POOL_A, POOL_B], topic0=SWAP_TOPIC)
        == []
    )

    (query,) = seen[0]["params"]  # type: ignore[misc]
    assert query["fromBlock"] == hex(100)
    assert query["toBlock"] == hex(1099)
    assert query["address"] == [POOL_A, POOL_B]
    assert query["topics"] == [SWAP_TOPIC]


def test_a_range_wider_than_the_node_allows_is_refused_before_it_is_sent() -> None:
    seen: list[dict[str, object]] = []
    node = HyperEvmNode(client_for(answering([], seen)))

    with pytest.raises(ValueError, match=str(MAX_BLOCK_RANGE)):
        node.logs(from_block=0, to_block=MAX_BLOCK_RANGE, addresses=[POOL_A], topic0=SWAP_TOPIC)

    assert seen == []


def test_the_widest_allowed_range_is_one_thousand_blocks_inclusive() -> None:
    node = HyperEvmNode(client_for(answering([])))

    node.logs(from_block=1, to_block=MAX_BLOCK_RANGE, addresses=[POOL_A], topic0=SWAP_TOPIC)

    assert MAX_BLOCK_RANGE == 1000


WORD = 64


def words(*values: int) -> str:
    return "0x" + "".join(format(v % (1 << 256), "064x") for v in values)


def test_a_uniswap_v3_pool_is_read_through_slot0_and_its_liquidity() -> None:
    seen: list[dict[str, object]] = []
    sqrt, tick = 2**96, -2000

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        call = body["params"][0]
        result = (
            words(5 * 10**18)
            if call["data"] == "0x1a686502"
            else words(sqrt, tick, 0, 0, 0, 0, 1)  # slot0
        )
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    node = HyperEvmNode(client_for(handle))

    from channelflow.dex.hyperevm_pools import POOLS

    reading = node.pool_reading(POOLS[0], block=1234)

    assert reading.active_liquidity == 5 * 10**18
    assert reading.sqrt_price_x96 == sqrt
    assert reading.tick == tick
    assert reading.fee_state == POOLS[0].fee_pips
    assert all(body["params"][1] == hex(1234) for body in seen)
    assert {body["params"][0]["data"] for body in seen} == {"0x1a686502", "0x3850c7bd"}


def test_an_algebra_pool_is_read_through_global_state_and_its_fee_is_the_published_one() -> None:
    sqrt, tick, last_fee = 2**96, 17, 1073

    def handle(request: httpx.Request) -> httpx.Response:
        call = json.loads(request.content)["params"][0]
        if call["data"] == "0x1a686502":
            result = words(9)
        elif call["data"] == "0xe76c01e4":  # globalState: the only state call Algebra answers
            result = words(sqrt, tick, last_fee, 0, 0, 1)
        else:
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1, "error": {"code": 3, "message": "reverted"}}
            )
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})

    from channelflow.dex.hyperevm_pools import POOLS

    reading = HyperEvmNode(client_for(handle)).pool_reading(POOLS[1], block=1)

    assert (reading.sqrt_price_x96, reading.tick, reading.fee_state) == (sqrt, tick, last_fee)
    assert reading.active_liquidity == 9


def test_a_reading_the_node_cut_short_is_a_failure_not_a_zero() -> None:
    from channelflow.dex.hyperevm_pools import POOLS

    with pytest.raises(RpcFailure):
        HyperEvmNode(client_for(answering("0x"))).pool_reading(POOLS[0], block=1)
