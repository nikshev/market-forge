"""One-shot recorder for a Uniswap v3 pool's own account of itself.

# @trace: REQ-WP-060

PRD section 18.7 reconstructs pool state from ordered events, and section
18.12.2 asks every reconstructed state to carry a `reconstruction_quality`.
This records the evidence that the field is load-bearing rather than
administrative.

The pool is Ethereum's deepest USDC/WETH pair. Two of its statements about the
same quantity are captured, and they are what makes a partial reconstruction
detectable without an archive node:

* every `Swap` reports the `liquidity` the pool had at that moment, so a replay
  of any window converges on the right **active** liquidity at its first swap;
* every `Mint` and `Burn` reports a tick range, and section 18.7.1's map
  accumulates only the ones the window saw.

A complete tick map satisfies `sum(liquidity_net for tick <= current) ==
active_liquidity`. Measured over 2,000 recent blocks, a replay sees fifteen
liquidity events against 1,366 swaps, so the map is nowhere near complete and
the two numbers disagree by everything.

**What that produces is not a smaller answer.** Over a 100-block window the
reconstruction succeeds, reports the correct active liquidity, and section
18.7.1's traversal then answers that fifty basis points is unreachable with
zero notional -- for the deepest pool on the chain. Over a 400-block window it
raises instead, because a burn happened to touch a range minted earlier. Which
of those two happens is luck.

Contrast with `hyperevm_capture.py`, deliberately: the same `eth_call` at a
recent historical block on these endpoints agrees with the logs exactly, so the
state oracle [[ADR-067]] gave up on chain 999 is available here.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.pool_state_capture
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eth_hash.auto import keccak

from tools.record.evm import EndpointPool, Refused, selector, word

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "pool_state"

RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://eth.merkle.io",
    "https://1rpc.io/eth",
    "https://rpc.mevblocker.io",
    "https://gateway.tenderly.co/public/mainnet",
)

CHAIN_ID = 1

#: USDC/WETH, 0.05%. The deepest pool on the chain, chosen because the failure
#: this fixture demonstrates is least believable there: a curve saying its price
#: cannot be moved at all is obviously wrong for *this* pool, and indisting-
#: uishable from a real answer for a small one.
POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
TOKEN0, TOKEN1 = "USDC", "WETH"
FEE_TIER, TICK_SPACING = 500, 10

SWAP_SIGNATURE = "Swap(address,address,int256,int256,uint160,uint128,int24)"
MINT_SIGNATURE = "Mint(address,address,int24,int24,uint128,uint256,uint256)"
BURN_SIGNATURE = "Burn(address,int24,int24,uint128,uint256,uint256)"
COLLECT_SIGNATURE = "Collect(address,address,int24,int24,uint128,uint128)"

#: Deep enough that a 400-block slice trips the existing negative-liquidity
#: guard and a 100-block slice does not, which is the pair of behaviours the
#: fixture exists to hold.
SCAN_BLOCKS = 2_000

WINDOW = 100

CONFIRMATIONS = 12


def topic0(signature: str) -> str:
    return "0x" + keccak(signature.encode()).hex()


TOPICS = {
    topic0(SWAP_SIGNATURE): "Swap",
    topic0(MINT_SIGNATURE): "Mint",
    topic0(BURN_SIGNATURE): "Burn",
    topic0(COLLECT_SIGNATURE): "Collect",
}


def signed(value: int, bits: int = 256) -> int:
    return value - (1 << bits) if value >= (1 << (bits - 1)) else value


def get_logs(pool: EndpointPool, low: int, high: int) -> list[dict[str, Any]]:
    """Never an empty list for a refusal: a quiet window and an absent one are
    different facts, and this fixture is about exactly that difference."""
    refusals = []
    for url in pool.healthy():
        try:
            return pool.rpc(
                url,
                "eth_getLogs",
                [{"address": POOL, "fromBlock": hex(low), "toBlock": hex(high)}],
            )
        except Refused as exc:
            refusals.append(str(exc))
    raise RuntimeError(f"no endpoint served logs for {low}-{high}: {refusals}")


def event_row(log: dict[str, Any]) -> dict[str, Any] | None:
    name = TOPICS.get(log["topics"][0])
    if name is None:
        return None
    body = log["data"].removeprefix("0x")
    word_at = lambda index: int(body[index * 64 : (index + 1) * 64], 16)  # noqa: E731
    row: dict[str, Any] = {
        "kind": name,
        "block_number": int(log["blockNumber"], 16),
        "transaction_index": int(log["transactionIndex"], 16),
        "log_index": int(log["logIndex"], 16),
        "topics": list(log["topics"]),
        "data": log["data"],
    }
    if name == "Swap":
        row |= {
            "amount0": str(signed(word_at(0))),
            "amount1": str(signed(word_at(1))),
            "sqrt_price_x96": str(word_at(2)),
            "liquidity": str(word_at(3)),
            "tick": signed(word_at(4)),
        }
    elif name in {"Mint", "Burn"}:
        # The ticks are indexed topics, sign extended to a full word.
        row |= {
            "tick_lower": signed(int(log["topics"][2], 16)),
            "tick_upper": signed(int(log["topics"][3], 16)),
            # `Mint` carries owner, tickLower, tickUpper as topics and
            # sender, amount, amount0, amount1 as data; `Burn` has no sender.
            "amount": str(word_at(1) if name == "Mint" else word_at(0)),
        }
    elif name == "Collect":
        row |= {"amount0": str(word_at(1)), "amount1": str(word_at(2))}
    return row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-block", type=int, default=None)
    parser.add_argument("--to-block", type=int, default=None)
    arguments = parser.parse_args(argv)
    if (arguments.from_block is None) != (arguments.to_block is None):
        raise SystemExit("--from-block and --to-block are given together or not at all")

    endpoints = EndpointPool(RPCS)
    if arguments.from_block is not None and arguments.to_block is not None:
        low, high = arguments.from_block, arguments.to_block
    else:
        head = int(endpoints.any_rpc("eth_blockNumber", []), 16) - CONFIRMATIONS
        low, high = head - SCAN_BLOCKS, head

    logs: list[dict[str, Any]] = []
    for start in range(low, high, WINDOW):
        logs += get_logs(endpoints, start, min(start + WINDOW - 1, high))

    rows = [row for row in (event_row(log) for log in logs) if row is not None]
    rows.sort(key=lambda row: (row["block_number"], row["transaction_index"], row["log_index"]))

    # The pool's own state at the scan's end. Available here and not on chain
    # 999: these endpoints serve a recent historical call from real state, and
    # the check below is what says so rather than assuming it.
    block = hex(high)
    slot0 = endpoints.call(POOL, selector("slot0()"), block)
    contract = {
        "kind": "contract_state",
        "block_number": high,
        "sqrt_price_x96": str(word(slot0, 0)),
        "tick": signed(word(slot0, 1)),
        "liquidity": str(word(endpoints.call(POOL, selector("liquidity()"), block))),
        "fee": word(endpoints.call(POOL, selector("fee()"), block)),
        "tick_spacing": word(endpoints.call(POOL, selector("tickSpacing()"), block)),
    }
    last_swap = next(row for row in reversed(rows) if row["kind"] == "Swap")
    counts = {name: sum(1 for row in rows if row["kind"] == name) for name in set(TOPICS.values())}

    header = {
        "kind": "scan",
        "chain_id": CHAIN_ID,
        "pool": POOL,
        "token0": TOKEN0,
        "token1": TOKEN1,
        "fee_tier": FEE_TIER,
        "tick_spacing": TICK_SPACING,
        "from_block": low,
        "to_block": high,
        "endpoints": list(RPCS),
        "events": len(rows),
        "counts": counts,
        # The contrast with ADR-067: here the contract and the logs agree, so a
        # historical read is evidence. Recorded as a measurement, not a claim.
        "contract_agrees_with_last_swap": (
            contract["liquidity"] == last_swap["liquidity"]
            and contract["tick"] == last_swap["tick"]
        ),
    }

    FIXTURES.mkdir(parents=True, exist_ok=True)
    with (FIXTURES / "uniswap_v3_events.jsonl").open("w") as handle:
        for row in [header, contract, *rows]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps(header, indent=2, sort_keys=True))
    print(json.dumps(contract, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
