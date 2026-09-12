"""One-shot recorder for Uniswap v4 `Initialize` logs: PoolId against PoolKey.

# @trace: REQ-WP-047

PRD section 18.25 requires that "PoolId routes to correct PoolKey", and a v4
`Initialize` log is the only fixture that can prove it: the event carries the
`PoolId` the singleton computed **and** every field of the `PoolKey` it computed
it from. So the mapping is checked against the chain's own hash rather than
against a reading of `PoolIdLibrary`.

That matters more than it sounds. `toId` is `keccak256(poolKey, 0xa0)` in
assembly -- five 32-byte slots, so ABI-*encoded* rather than packed, with
`int24 tickSpacing` sign-extended across a full word. Packing it, or extending
the sign wrongly, produces a 32-byte value that looks exactly as much like a
pool id as the right one.

**The manager address is discovered, not recalled.** This scans for the
`Initialize` topic and refuses if more than one contract emitted it, which also
records section 18.8.2's point as a measurement: every pool on the chain emits
through one address, so filtering by address is not routing.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.uniswap_v4_capture
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from eth_hash.auto import keccak

from tools.record.evm import EndpointPool, signed, word

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "uniswap_v4"

RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://1rpc.io/eth",
    "https://eth.merkle.io",
    "https://eth-pokt.nodies.app",
    "https://gateway.tenderly.co/public/mainnet",
    "https://rpc.mevblocker.io",
)

INITIALIZE = "Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)"

#: How far back to scan. Deep enough to find several thousand pools and, with
#: them, a spread of hook addresses; shallow enough for a node with no archive.
SCAN_BLOCKS = 40_000

CONFIRMATIONS = 12

#: How many pools to keep per hook shape. The point is coverage of the shapes
#: section 18.8.1 classifies, not a census.
PER_SHAPE = 4

#: Uniswap's flag layout, from `Hooks.sol`. The permissions are in the hook
#: *address*, which is why a classification needs no call.
ALL_HOOK_MASK = (1 << 14) - 1
RETURNS_DELTA_MASK = 0b1111  # bits 0-3: the four "returns delta" permissions

DYNAMIC_FEE_FLAG = 0x800000


def _shape(hooks: str, fee: int) -> str:
    """A coarse label, only so the sample spans what matters."""
    bits = int(hooks, 16) & ALL_HOOK_MASK
    if bits & RETURNS_DELTA_MASK:
        return "returns_delta"
    if fee == DYNAMIC_FEE_FLAG:
        return "dynamic_fee"
    if bits:
        return "hooked"
    if int(hooks, 16) == 0:
        return "no_hook"
    return "hook_without_flags"


def main() -> None:
    pool_of = EndpointPool(RPCS)
    topic = "0x" + keccak(INITIALIZE.encode()).hex()
    head = int(pool_of.any_rpc("eth_blockNumber", []), 16)
    to_block = head - CONFIRMATIONS
    from_block = to_block - SCAN_BLOCKS
    print(f"scanning {from_block}..{to_block} for {topic}")

    logs = pool_of.any_rpc(
        "eth_getLogs",
        [{"fromBlock": hex(from_block), "toBlock": hex(to_block), "topics": [topic]}],
    )
    if not isinstance(logs, list) or not logs:
        raise SystemExit("no Initialize logs in range")

    emitters = Counter(entry["address"].lower() for entry in logs)
    if len(emitters) != 1:
        raise SystemExit(f"expected one singleton manager, found {dict(emitters)}")
    manager = next(iter(emitters))
    print(f"{len(logs)} pools initialised, all through {manager}")

    by_shape: dict[str, list[dict[str, Any]]] = {}
    for entry in logs:
        # Indexed: id, currency0, currency1. Non-indexed, in order:
        # fee, tickSpacing, hooks, sqrtPriceX96, tick.
        data = entry["data"]
        fee = word(data, 0)
        tick_spacing = signed(data, 1)
        hooks = "0x" + data[2:][2 * 64 : 3 * 64][-40:]
        record = {
            "block": int(entry["blockNumber"], 16),
            "pool_id": entry["topics"][1],
            "currency0": "0x" + entry["topics"][2][-40:],
            "currency1": "0x" + entry["topics"][3][-40:],
            "fee": fee,
            "tick_spacing": tick_spacing,
            "hooks": hooks,
            "sqrt_price_x96": str(word(data, 3)),
            "tick": signed(data, 4),
        }
        shape = _shape(hooks, fee)
        record["shape"] = shape
        bucket = by_shape.setdefault(shape, [])
        if len(bucket) < PER_SHAPE:
            bucket.append(record)

    for shape, bucket in sorted(by_shape.items()):
        print(f"  {shape:>18}: {len(bucket)} kept")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "initialize.jsonl"
    rows: list[dict[str, Any]] = [
        {
            "kind": "manager",
            "manager": manager,
            "topic0": topic,
            "from_block": from_block,
            "to_block": to_block,
            "pools_initialised": len(logs),
            "distinct_emitters": len(emitters),
        }
    ]
    for bucket in by_shape.values():
        rows += [{"kind": "pool", **record} for record in bucket]
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    )
    print(f"  {path.name}: {len(rows)}")


if __name__ == "__main__":
    main()
