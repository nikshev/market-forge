"""One-shot recorder for Aerodrome Slipstream pool identity and swap fees.

# @trace: REQ-WP-045

Slipstream is a Uniswap v3 fork, and that is the trap. Its `Swap` event's
signature is byte-identical to Uniswap v3's, so the topic hash a v3 decoder
matches on is the same one, and every field decodes correctly. What differs is
never the event:

* the pool key is `(token0, token1, tickSpacing)`, not `(token0, token1, fee)`,
  and the factory's own tick-spacing table is not injective -- spacings 10, 50
  and 100 all default to 500 -- so neither can be derived from the other;
* `CLPool.fee()` forwards to `ICLFactory.getSwapFee(pool)`, which forwards to a
  fee module, and the module in force on Base computes the fee from the pool's
  own recent tick movement. It changes every block, with no transaction and no
  event to subscribe to.

So this records what cannot be derived: the enabled tick spacings and their
defaults, the fee module's configuration, and -- for each sampled pool -- every
input the module reads plus the answer the chain gives. That makes the fixture
an oracle rather than a recording, exactly as the v2 capture's `getAmountOut`
is, and lets the adapter be held to equality rather than tolerance.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.slipstream_capture

Addresses come from Slipstream's own published deployment output
(`script/constants/output/DeployCL-Base.json`) and are confirmed live here by
reading `allPoolsLength()` before anything else is trusted. Everything is read
at one pinned block: a fee assembled across blocks would pair one block's tick
with another block's average, and the adapter would be tested against an
arithmetic that never existed.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from eth_hash.auto import keccak

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "aerodrome"

#: Candidate endpoints. PRD section 18.17 asks for a multi-RPC strategy, and
#: every call below is answered by two of these independently: a value both
#: agree on is a value, and a value they disagree on is a finding.
#:
#: There are five rather than two because free endpoints rate-limit a sustained
#: capture, and an endpoint that starts refusing mid-run should cost the run an
#: endpoint rather than the run. Two healthy ones are always required -- the
#: pool degrades, the guarantee does not.
RPCS = (
    "https://mainnet.base.org",
    "https://base-rpc.publicnode.com",
    "https://base.drpc.org",
    "https://1rpc.io/base",
    "https://gateway.tenderly.co/public/base",
)

#: How long an endpoint that refuses stays out of the rotation.
COOLDOWN_SECONDS = 90.0

#: Slipstream's `PoolFactory` on Base, from the project's own DeployCL-Base.json.
#: Two later CL factories exist (the gauge-caps and min-unstake deployments);
#: this is the original and by far the largest, which is what a fixture wants.
CL_FACTORY = "0x5e7BB104d84c7CB9B682AaC2F3d509f5F406809A"

HEADERS = {"Content-Type": "application/json", "User-Agent": "channelflow-capture/1.0"}

#: How many of the factory's pools to look at, and how many to keep. The point
#: is a handful of real fees spanning the module's branches -- a pool with no
#: dynamic term, a pool with one, a pool at its cap -- not a survey of a venue.
SAMPLE = 60
KEEP = 8

PAUSE_SECONDS = 0.35


def selector(signature: str) -> str:
    return "0x" + keccak(signature.encode())[:4].hex()


#: When each endpoint may next be used. An endpoint that refused is not broken,
#: it is busy, and asking it again immediately is how a capture tool turns a
#: rate limit into a failed run.
_AVAILABLE_AT: dict[str, float] = dict.fromkeys(RPCS, 0.0)


class Refused(RuntimeError):
    """An endpoint declined this request. Another may not."""


def _rpc(url: str, method: str, params: list[Any]) -> Any:
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers=HEADERS,
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            body = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError) as exc:
        _AVAILABLE_AT[url] = time.monotonic() + COOLDOWN_SECONDS
        raise Refused(f"{url}: {exc}") from exc
    if "error" in body:
        # A contract-level revert is a fact about the call: every endpoint would
        # say the same thing, so it must not cool one off -- treating it as a
        # refusal would burn the whole pool on one reverting call. Anything else
        # an endpoint objects to (a method it declines to serve, a block it has
        # pruned) is about the endpoint, and another may answer.
        error = body["error"]
        if "data" in error or "revert" in str(error.get("message", "")).lower():
            raise RuntimeError(f"{method}: {error}")
        _AVAILABLE_AT[url] = time.monotonic() + COOLDOWN_SECONDS
        raise Refused(f"{url}: {error}")
    return body["result"]


def _healthy() -> list[str]:
    now = time.monotonic()
    return [url for url in RPCS if _AVAILABLE_AT[url] <= now]


def call(to: str, data: str, block: str) -> str:
    """One `eth_call`, asked of two healthy endpoints and refused if they differ."""
    params = [{"to": to, "data": data}, block]
    answers: dict[str, str] = {}
    for url in _healthy():
        if len(answers) == 2:
            break
        try:
            answers[url] = _rpc(url, "eth_call", params)
        except Refused:  # noqa: PERF203
            continue
    if len(answers) < 2:
        raise RuntimeError(
            f"fewer than two endpoints answered {to} {data[:10]} at {block}; healthy: {_healthy()}"
        )
    distinct = set(answers.values())
    if len(distinct) != 1:
        raise RuntimeError(f"endpoints disagree on {to} {data[:10]} at {block}: {answers}")
    time.sleep(PAUSE_SECONDS)
    return distinct.pop()


def _word(result: str, index: int = 0) -> int:
    raw = result[2:]
    return int(raw[index * 64 : (index + 1) * 64], 16)


def _signed(result: str, index: int = 0) -> int:
    value = _word(result, index)
    return value - (1 << 256) if value >= (1 << 255) else value


def _address(result: str, index: int = 0) -> str:
    return "0x" + result[2:][index * 64 : (index + 1) * 64][-40:]


def _encode_uint(value: int) -> str:
    return f"{value & ((1 << 256) - 1):064x}"


def _encode_address(value: str) -> str:
    return f"{int(value, 16):064x}"


def _spacing_defaults(block: str) -> dict[str, int]:
    """Every enabled tick spacing and the fee the factory defaults it to.

    This is the table a Uniswap v3 decoder would reach for, and recording it is
    how the adapter's tests can show that it is not the fee anyone pays.
    """
    packed = call(CL_FACTORY, selector("tickSpacings()"), block)
    count = _word(packed, 1)
    return {
        str(_signed(packed, 2 + index)): _word(
            call(
                CL_FACTORY,
                selector("tickSpacingToFee(int24)") + _encode_uint(_signed(packed, 2 + index)),
                block,
            )
        )
        for index in range(count)
    }


def _tick_cumulatives(pool: str, seconds_ago: int, block: str) -> list[int] | None:
    """`observe([secondsAgo, 0])`, or None where the module's `try` would catch.

    A pool whose oracle does not reach back far enough reverts with `OLD`, and
    the module answers zero rather than failing. A fixture that dropped such a
    pool would leave that branch untested against the chain.
    """
    payload = (
        selector("observe(uint32[])")
        + _encode_uint(32)
        + _encode_uint(2)
        + _encode_uint(seconds_ago)
        + _encode_uint(0)
    )
    try:
        result = call(pool, payload, block)
    except RuntimeError:
        return None
    offset = _word(result, 0) // 32
    return [_signed(result, offset + 1), _signed(result, offset + 2)]


def main() -> None:
    head = int(_rpc(RPCS[0], "eth_blockNumber", []), 16)
    # Pinned, and a little behind the head so a reorg cannot move it under the
    # fixture between the read and the commit.
    block = hex(head - 32)
    print(f"pinned block {int(block, 16)}")

    length = _word(call(CL_FACTORY, selector("allPoolsLength()"), block))
    module = _address(call(CL_FACTORY, selector("swapFeeModule()"), block))
    print(f"factory holds {length} pools; swap fee module {module}")

    defaults = _spacing_defaults(block)
    print(f"enabled tick spacings: {defaults}")

    seconds_ago = _word(call(module, selector("secondsAgo()"), block))
    module_config = {
        "module": module,
        "default_scaling_factor": str(
            _word(call(module, selector("defaultScalingFactor()"), block))
        ),
        "default_fee_cap": _word(call(module, selector("defaultFeeCap()"), block)),
        "seconds_ago": seconds_ago,
    }
    print(f"module config: {module_config}")

    records: list[dict[str, Any]] = []
    for index in range(min(SAMPLE, length)):
        if len(records) >= KEEP:
            break
        pool = _address(
            call(CL_FACTORY, selector("allPools(uint256)") + _encode_uint(index), block)
        )
        if _word(call(pool, selector("liquidity()"), block)) == 0:
            continue

        slot0 = call(pool, selector("slot0()"), block)
        config = call(module, selector("dynamicFeeConfig(address)") + _encode_address(pool), block)
        spacing = _signed(call(pool, selector("tickSpacing()"), block))
        cardinality = _word(slot0, 3)
        record = {
            "kind": "pool",
            "block": int(block, 16),
            "pool": pool,
            "token0": _address(call(pool, selector("token0()"), block)),
            "token1": _address(call(pool, selector("token1()"), block)),
            "tick_spacing": spacing,
            "tick": _signed(slot0, 1),
            "observation_cardinality": cardinality,
            "base_fee": _word(config, 0),
            "fee_cap": _word(config, 1),
            "scaling_factor": str(_word(config, 2)),
            "initial_fee_enabled": bool(_word(config, 3)),
            "initial_fee": _word(config, 4),
            "tick_cumulatives": _tick_cumulatives(pool, seconds_ago, block),
            # Both, deliberately. `CLPool.fee()` forwards to the factory, so
            # these must agree at one block, and a fixture recording only one
            # could not show it.
            "pool_fee": _word(call(pool, selector("fee()"), block)),
            "factory_fee": _word(
                call(CL_FACTORY, selector("getSwapFee(address)") + _encode_address(pool), block)
            ),
        }
        records.append(record)
        print(
            f"  {pool} spacing={spacing:>5} fee={record['pool_fee']:>6} "
            f"default={defaults[str(spacing)]:>6} base={record['base_fee']:>6} "
            f"K={record['scaling_factor']}"
        )

    if not records:
        raise SystemExit(f"no pool with liquidity in the first {SAMPLE}")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "slipstream_pools.jsonl"
    lines: list[dict[str, Any]] = [
        {"kind": "factory", "block": int(block, 16), "factory": CL_FACTORY, "defaults": defaults},
        {"kind": "module", "block": int(block, 16), **module_config},
    ]
    lines += records
    path.write_text(
        "".join(json.dumps(line, sort_keys=True, separators=(",", ":")) + "\n" for line in lines)
    )
    print(f"  {path.name}: {len(lines)}")


if __name__ == "__main__":
    main()
