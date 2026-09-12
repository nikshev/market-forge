"""One-shot recorder for HyperEVM DEX swaps and HyperCore cross-layer transfers.

# @trace: REQ-WP-058

PRD section 18.11.2 says a HyperEVM AMM "is analyzed according to **its AMM
protocol**". This records the two measurements that make that sentence load
bearing rather than obvious.

**The event signature does not name the protocol.** The busiest two WHYPE/USDC
pools on chain 999 emit the identical `Swap` topic0 with the identical five-word
payload, and they are different protocols: one is a Uniswap v3 factory whose
`fee()` is immutable, the other an Algebra Integral factory whose fee is set per
swap by a plugin and published as a separate `Fee(uint16)` log. Decoding either
one with the other's fee produces a number that is positive, ordered and wrong.

**A cross-layer transfer is an ordinary ERC-20 `Transfer` to an address with no
code.** The HyperCore spot index is the low bits of that address, and the amount
is not the HyperCore amount: `spotMeta` carries `evm_extra_wei_decimals` per
token, measured here as -2 for USDC and +10 for FLOCK. Reading the log's amount
as the credited amount is wrong by twelve orders of magnitude between those two,
and looks like a balance either way.

**The state oracle the other capture tools use is not available here.** The
public HyperEVM endpoints are not archive nodes: asked for `slot0()` at a block
a few hundred behind the head they return near-head state, and two of them
disagree about it. So nothing in this file verifies a decode against historical
contract state. What it records instead is the ERC-20 `Transfer` set of each
swap's own transaction, which is a log-only oracle -- `amount0` and `amount1`
must equal the pool's net token movement in that transaction -- and therefore
immune to the problem. See ADR-067.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.hyperevm_capture
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from eth_hash.auto import keccak

from tools.record.evm import EndpointPool, Refused, Reverted, selector, word

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "hyperevm"

RPCS = (
    "https://rpc.hyperliquid.xyz/evm",
    "https://rpc.hypurrscan.io",
    "https://hyperliquid.drpc.org",
)

CHAIN_ID = 999

HYPERCORE_INFO = "https://api.hyperliquid.xyz/info"

#: The two busiest WHYPE/USDC pools on the chain, found by counting `Swap`
#: emitters over 800 blocks. Pinned here because the point of the fixture is
#: these two specific protocols, not whatever is busiest on the day it reruns.
POOLS = (
    "0x6c9a33e3b592c0d65b3ba59355d5be0d38259285",
    "0xbe512f5881b85c48d9c17bc5bb2be047d156d696",
)

SWAP_SIGNATURE = "Swap(address,address,int256,int256,uint160,uint128,int24)"
FEE_SIGNATURE = "Fee(uint16)"
TRANSFER_SIGNATURE = "Transfer(address,address,uint256)"

#: Where HyperCore's spot assets appear on HyperEVM: `0x2000...0000 + index`.
#: These addresses hold no code, which is the check the capture records rather
#: than a claim it repeats.
SYSTEM_PREFIX = "0x2000000000000000000000000000000000000"

#: The base those addresses count up from. The HyperCore spot index is the
#: difference, not the address read as an integer -- a distinction worth a
#: constant, because reading the whole address as the index yields a number
#: that is large, stable and never matches anything.
SYSTEM_BASE = 0x2000000000000000000000000000000000000000

#: Window sizes these endpoints accept. A wider `eth_getLogs` is refused
#: outright, and a refusal that returned an empty list would read as "nothing
#: happened" -- so every window here either answers or raises.
POOL_WINDOW = 50
TOPIC_WINDOW = 25

#: How far back to scan. Deep enough for a few dozen swaps across both
#: protocols and a handful of cross-layer transfers.
SCAN_BLOCKS = 900

#: Blocks behind the head. These endpoints serve recent state and logs; this is
#: only so a reorg cannot change what was written.
CONFIRMATIONS = 12


def topic0(signature: str) -> str:
    return "0x" + keccak(signature.encode()).hex()


SWAP = topic0(SWAP_SIGNATURE)
FEE = topic0(FEE_SIGNATURE)
TRANSFER = topic0(TRANSFER_SIGNATURE)


def signed_word(data: str, index: int, bits: int = 256) -> int:
    """One ABI word read as a signed integer.

    `int24` arrives sign-extended across a full word, so the width that matters
    for the sign test is 256 whatever the declared type -- reading `tick` as a
    24-bit two's complement of the low bytes yields a large positive number
    instead of a small negative one.
    """
    value = int(data[index * 64 : (index + 1) * 64], 16)
    return value - (1 << bits) if value >= (1 << (bits - 1)) else value


def get_logs(pool: EndpointPool, request: dict[str, Any]) -> list[dict[str, Any]]:
    """`eth_getLogs` from whichever endpoint answers, or raise.

    Never returns an empty list for a refusal: an absent window and a quiet
    window are different facts and the difference is the whole capture.
    """
    refusals = []
    for url in pool.healthy():
        try:
            return pool.rpc(url, "eth_getLogs", [request])
        except Refused as exc:
            refusals.append(str(exc))
    raise RuntimeError(f"no endpoint served eth_getLogs {request}: {refusals}")


def receipt(pool: EndpointPool, transaction: str) -> dict[str, Any]:
    refusals = []
    for url in pool.healthy():
        try:
            return pool.rpc(url, "eth_getTransactionReceipt", [transaction])
        except Refused as exc:
            refusals.append(str(exc))
    raise RuntimeError(f"no endpoint served a receipt for {transaction}: {refusals}")


def try_call(pool: EndpointPool, to: str, signature: str, block: str) -> str | None:
    """A capability probe. A revert is an answer; a refusal is not."""
    try:
        return pool.call(to, selector(signature), block)
    except Reverted:
        return None


def spot_meta() -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310
        HYPERCORE_INFO,
        data=json.dumps({"type": "spotMeta"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
        return json.loads(response.read())


def describe_pool(pool: EndpointPool, address: str, block: str) -> dict[str, Any]:
    """What the pool says it is, by which calls it answers.

    `globalState()` and `plugin()` are Algebra Integral; `slot0()` is Uniswap
    v3. Both answer `fee()`, and that is the point: the number means different
    things on either side.
    """
    algebra = try_call(pool, address, "globalState()", block)
    univ3 = try_call(pool, address, "slot0()", block)
    plugin = try_call(pool, address, "plugin()", block)
    factory = try_call(pool, address, "factory()", block)
    fee = try_call(pool, address, "fee()", block)
    return {
        "kind": "pool",
        "address": address,
        "factory": None if factory is None else "0x" + factory[-40:],
        "family": "algebra_integral" if algebra is not None else "uniswap_v3",
        "answers_global_state": algebra is not None,
        "answers_slot0": univ3 is not None,
        "plugin": None if plugin is None else "0x" + plugin[-40:],
        "token0": "0x" + (try_call(pool, address, "token0()", block) or "")[-40:],
        "token1": "0x" + (try_call(pool, address, "token1()", block) or "")[-40:],
        "tick_spacing": word(try_call(pool, address, "tickSpacing()", block) or "0x0"),
        # Read now, not at `to_block`: these endpoints have no archive and
        # would answer a historical call with this same number anyway (ADR-067).
        # It is recorded because it is the trap -- the fee a decoder would use
        # if it asked the pool instead of reading the log.
        "fee_at_capture": None if fee is None else word(fee),
        "state_words": None if algebra is None else (len(algebra) - 2) // 64,
    }


def swap_rows(pool: EndpointPool, address: str, low: int, high: int) -> list[dict[str, Any]]:
    """Every `Swap` in the range, with the `Fee` log and transfers that explain it."""
    logs: list[dict[str, Any]] = []
    for start in range(low, high, POOL_WINDOW):
        logs += get_logs(
            pool,
            {
                "address": address,
                "fromBlock": hex(start),
                "toBlock": hex(min(start + POOL_WINDOW - 1, high)),
            },
        )
    by_transaction: dict[str, list[dict[str, Any]]] = {}
    for log in logs:
        by_transaction.setdefault(log["transactionHash"], []).append(log)

    rows = []
    for log in sorted(
        (entry for entry in logs if entry["topics"][0] == SWAP),
        key=lambda entry: (int(entry["blockNumber"], 16), int(entry["logIndex"], 16)),
    ):
        index = int(log["logIndex"], 16)
        siblings = by_transaction[log["transactionHash"]]
        # The fee for this swap is the last `Fee` log before it in the same
        # transaction: one transaction can hold several swaps on one pool, and
        # the plugin publishes a fee before each.
        preceding = [
            entry
            for entry in siblings
            if entry["topics"][0] == FEE and int(entry["logIndex"], 16) < index
        ]
        fee_log = (
            max(preceding, key=lambda entry: int(entry["logIndex"], 16)) if preceding else None
        )
        transfers = [
            {
                "token": entry["address"].lower(),
                "topics": list(entry["topics"]),
                "data": entry["data"],
                "from": "0x" + entry["topics"][1][-40:],
                "to": "0x" + entry["topics"][2][-40:],
                "amount": str(int(entry["data"], 16)),
                "log_index": int(entry["logIndex"], 16),
            }
            for entry in receipt(pool, log["transactionHash"])["logs"]
            if entry["topics"][0] == TRANSFER and len(entry["topics"]) == 3
        ]
        data = log["data"][2:]
        rows.append(
            {
                "kind": "swap",
                "pool": address,
                "block": int(log["blockNumber"], 16),
                "log_index": index,
                "transaction": log["transactionHash"],
                "topics": list(log["topics"]),
                "topic0": log["topics"][0],
                "data": log["data"],
                "sender": "0x" + log["topics"][1][-40:],
                "recipient": "0x" + log["topics"][2][-40:],
                "amount0": str(signed_word(data, 0)),
                "amount1": str(signed_word(data, 1)),
                "sqrt_price_x96": str(int(data[2 * 64 : 3 * 64], 16)),
                "liquidity": str(int(data[3 * 64 : 4 * 64], 16)),
                "tick": signed_word(data, 4),
                "fee_log_index": None if fee_log is None else int(fee_log["logIndex"], 16),
                "fee_pips": None if fee_log is None else int(fee_log["data"], 16),
                "swaps_in_transaction": sum(1 for entry in siblings if entry["topics"][0] == SWAP),
                "transfers": transfers,
            }
        )
    return rows


def system_transfer_rows(
    pool: EndpointPool, low: int, high: int, tokens: dict[str, Any]
) -> list[dict[str, Any]]:
    """ERC-20 transfers into or out of a HyperCore system address."""
    rows = []
    for start in range(low, high, TOPIC_WINDOW):
        logs = get_logs(
            pool,
            {
                "fromBlock": hex(start),
                "toBlock": hex(min(start + TOPIC_WINDOW - 1, high)),
                "topics": [TRANSFER],
            },
        )
        for log in logs:
            if len(log["topics"]) != 3:
                continue
            sender = "0x" + log["topics"][1][-40:]
            recipient = "0x" + log["topics"][2][-40:]
            system = next(
                (a for a in (sender, recipient) if a.lower().startswith(SYSTEM_PREFIX)),
                None,
            )
            if system is None:
                continue
            token = tokens.get(log["address"].lower())
            rows.append(
                {
                    "kind": "system_transfer",
                    "token": log["address"].lower(),
                    "block": int(log["blockNumber"], 16),
                    "log_index": int(log["logIndex"], 16),
                    "transaction": log["transactionHash"],
                    "topics": list(log["topics"]),
                    "data": log["data"],
                    "from": sender,
                    "to": recipient,
                    "amount": str(int(log["data"], 16)),
                    "direction": "to_core" if system == recipient else "to_evm",
                    "system_address": system,
                    "system_address_index": int(system, 16) - SYSTEM_BASE,
                    "system_address_has_code": len(pool.any_rpc("eth_getCode", [system, "latest"]))
                    - 2,
                    "core_name": None if token is None else token["name"],
                    "core_index": None if token is None else token["index"],
                    "wei_decimals": None if token is None else token["weiDecimals"],
                    "evm_extra_wei_decimals": None
                    if token is None
                    else token["evmContract"]["evm_extra_wei_decimals"],
                }
            )
    return rows


def main(argv: list[str] | None = None) -> None:
    """Scan back from the head, or re-record a range already captured.

    The range override exists because a fixture sometimes needs a field it was
    not recorded with, and re-scanning from the head would move every number
    the notes quote. Re-recording the same blocks changes the file and nothing
    else.
    """
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
    block = hex(high)

    meta = spot_meta()
    tokens = {
        token["evmContract"]["address"].lower(): token
        for token in meta["tokens"]
        if token.get("evmContract")
    }

    # Every spot asset that has an EVM contract, not only the ones a transfer
    # happened to touch. `evm_extra_wei_decimals` is what converts a transfer
    # amount to the amount HyperCore credits, and the sample of tokens moving
    # in any four hundred blocks does not span its range -- so the conversion
    # would be tested only in the direction the window happened to catch.
    assets = [
        {
            "kind": "core_asset",
            "name": token["name"],
            "index": token["index"],
            "evm_contract": token["evmContract"]["address"].lower(),
            "evm_extra_wei_decimals": token["evmContract"]["evm_extra_wei_decimals"],
            "wei_decimals": token["weiDecimals"],
            "sz_decimals": token["szDecimals"],
            "is_canonical": token["isCanonical"],
        }
        for token in meta["tokens"]
        if token.get("evmContract")
    ]

    pools = [describe_pool(endpoints, address, block) for address in POOLS]
    swaps: list[dict[str, Any]] = []
    for address in POOLS:
        swaps += swap_rows(endpoints, address, low, high)
    transfers = system_transfer_rows(endpoints, low, high, tokens)

    families = Counter(row["family"] for row in pools)
    header = {
        "kind": "scan",
        "chain_id": CHAIN_ID,
        "from_block": low,
        "to_block": high,
        "endpoints": list(RPCS),
        "swap_topic0": SWAP,
        "fee_topic0": FEE,
        "transfer_topic0": TRANSFER,
        "pools": len(pools),
        "families": dict(families),
        "swaps": len(swaps),
        "swaps_with_fee_log": sum(1 for row in swaps if row["fee_pips"] is not None),
        "system_transfers": len(transfers),
        "spot_tokens_with_evm_contract": len(tokens),
        "spot_tokens_total": len(meta["tokens"]),
        "evm_extra_wei_decimals_range": [
            min(row["evm_extra_wei_decimals"] for row in assets),
            max(row["evm_extra_wei_decimals"] for row in assets),
        ],
    }

    FIXTURES.mkdir(parents=True, exist_ok=True)
    with (FIXTURES / "swaps.jsonl").open("w") as handle:
        for row in [header, *pools, *swaps]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    with (FIXTURES / "cross_layer.jsonl").open("w") as handle:
        for row in [header, *assets, *transfers]:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    print(json.dumps(header, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
