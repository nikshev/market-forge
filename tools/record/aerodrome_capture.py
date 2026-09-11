"""One-shot recorder for Aerodrome v2 pool state and the contract's own quotes.

# @trace: REQ-WP-045

PRD section 18.25 requires every protocol adapter's "quote curve matches
contract view within tolerance". An Aerodrome v2 pool exposes
`getAmountOut(amountIn, tokenIn)` -- its own answer to precisely the question
the adapter computes -- so the fixture is not a recording of what the venue
said, it is the authority's answer.

That makes this stronger than the exchange capture tools. There the recording
was evidence about a format; here the chain is the oracle for a number.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.aerodrome_capture

Writes newline-delimited JSON under tests/fixtures/aerodrome/. No credentials:
Base's public RPC answers without a key, and two independent endpoints are
queried so a single node's answer is never the whole record.

**Every read is pinned to one block.** A fixture assembled across blocks would
mix reserves from one state with a quote from another, and the adapter would be
tested against an arithmetic that never existed.

Selectors are computed from signatures taken from Aerodrome's published
`Pool.sol`, not copied from anywhere: a selector is the hash of a signature, and
computing it is how a typo becomes an error instead of a wrong call.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

from eth_hash.auto import keccak

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "aerodrome"

#: Two independent endpoints. PRD section 18.17 asks for a multi-RPC strategy
#: and the reason shows up immediately: a value both agree on is a value, and a
#: value they disagree on is a finding.
RPCS = ("https://mainnet.base.org", "https://base-rpc.publicnode.com")

#: Labelled on BaseScan as "Aerodrome: Pool Factory"; confirmed live by reading
#: `allPoolsLength()` from it.
POOL_FACTORY = "0x420dd381b31aef6683db6b902084cb0ffece40da"

HEADERS = {"Content-Type": "application/json", "User-Agent": "channelflow-capture/1.0"}

#: How many of the factory's pools to look at. The oldest are the deepest, and
#: the point is to find one pool of each curve rather than to survey the venue.
SAMPLE = 30

#: A breath between calls. Free endpoints rate-limit, and a tool that ignored
#: that would be taking from a commons to save itself half a minute.
PAUSE_SECONDS = 0.35


def selector(signature: str) -> str:
    return "0x" + keccak(signature.encode())[:4].hex()


def _rpc(url: str, method: str, params: list[Any]) -> Any:
    """One JSON-RPC call, backing off when a free endpoint says to.

    These are public nodes nobody pays for, and a capture tool that hammered
    them would be taking from a commons to save itself thirty seconds. The
    retry is on 429 specifically: any other error is a fact about the request
    and should surface.
    """
    request = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers=HEADERS,
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                body = json.loads(response.read())
            break
        except urllib.error.HTTPError as exc:  # noqa: PERF203
            if exc.code != 429 or attempt == 5:
                raise
            time.sleep(2**attempt)
    if "error" in body:
        raise RuntimeError(f"{method}: {body['error']}")
    time.sleep(PAUSE_SECONDS)
    return body["result"]


def call(to: str, data: str, block: str) -> str:
    """One `eth_call`, asked of both endpoints and refused if they differ."""
    answers = {url: _rpc(url, "eth_call", [{"to": to, "data": data}, block]) for url in RPCS}
    distinct = set(answers.values())
    if len(distinct) != 1:
        raise RuntimeError(f"endpoints disagree on {to} {data[:10]} at {block}: {answers}")
    return distinct.pop()


def _word(result: str, index: int = 0) -> int:
    raw = result[2:]
    return int(raw[index * 64 : (index + 1) * 64], 16)


def _address(result: str, index: int = 0) -> str:
    return "0x" + result[2:][index * 64 : (index + 1) * 64][-40:]


def _encode_uint(value: int) -> str:
    return f"{value:064x}"


def _encode_address(value: str) -> str:
    return f"{int(value, 16):064x}"


def main() -> None:
    block_number = int(_rpc(RPCS[0], "eth_blockNumber", []), 16)
    # Pinned, and a little behind the head so a reorg cannot move it under the
    # fixture between the read and the commit.
    block = hex(block_number - 32)
    print(f"pinned block {int(block, 16)}")

    length = _word(call(POOL_FACTORY, selector("allPoolsLength()"), block))
    print(f"factory holds {length} pools")

    found: dict[bool, dict[str, Any]] = {}
    for index in range(min(SAMPLE, length)):
        if len(found) == 2:
            break
        pool = _address(
            call(POOL_FACTORY, selector("allPools(uint256)") + _encode_uint(index), block)
        )
        stable = bool(_word(call(pool, selector("stable()"), block)))
        if stable in found:
            continue

        reserves = call(pool, selector("getReserves()"), block)
        reserve0, reserve1 = _word(reserves, 0), _word(reserves, 1)
        if reserve0 == 0 or reserve1 == 0:
            continue

        token0 = _address(call(pool, selector("token0()"), block))
        token1 = _address(call(pool, selector("token1()"), block))
        decimals0 = _word(call(token0, selector("decimals()"), block))
        decimals1 = _word(call(token1, selector("decimals()"), block))
        fee_bps = _word(
            call(
                POOL_FACTORY,
                selector("getFee(address,bool)")
                + _encode_address(pool)
                + _encode_uint(int(stable)),
                block,
            )
        )

        # The contract's own answers, across four orders of magnitude, so a
        # quote that is right at one size and wrong at another cannot pass.
        quotes = []
        for scale in (2, 3, 4, 5):
            amount_in = 10 ** (decimals0 - 6 + scale) if decimals0 >= 6 else 10**scale
            if amount_in <= 0:
                continue
            out = _word(
                call(
                    pool,
                    selector("getAmountOut(uint256,address)")
                    + _encode_uint(amount_in)
                    + _encode_address(token0),
                    block,
                )
            )
            quotes.append({"amount_in": str(amount_in), "token_in": token0, "amount_out": str(out)})

        found[stable] = {
            "block": int(block, 16),
            "pool": pool,
            "stable": stable,
            "token0": token0,
            "token1": token1,
            "decimals0": decimals0,
            "decimals1": decimals1,
            "reserve0": str(reserve0),
            "reserve1": str(reserve1),
            "fee_bps": fee_bps,
            "quotes": quotes,
        }
        print(f"  {'stable  ' if stable else 'volatile'} {pool} fee={fee_bps}bps")

    if len(found) != 2:
        raise SystemExit(f"only found {sorted(found)} in the first {SAMPLE} pools")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    for stable, record in found.items():
        name = "v2_stable" if stable else "v2_volatile"
        path = FIXTURES / f"{name}.jsonl"
        path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        print(f"  {path.name}: 1")


if __name__ == "__main__":
    main()
