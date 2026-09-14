"""One-shot recorder for Uniswap v4 quotes on `CUSTOM_ACCOUNTING` pools.

# @trace: REQ-WP-071

PRD section 18.8.1 says of these pools: *"do not assume the standard curve;
prefer executable quoting/simulation adapter."* This captures what both sides of
that sentence actually say about the same pools at the same block, so the
adapter's tests can replay it without a network.

Three things this tool refuses to take on trust:

* **The quoter is identified by the manager it names.** A quoter address is
  recalled, and recollection is not evidence. This calls `poolManager()` on the
  candidate and refuses unless the answer is the singleton the fixture's
  `Initialize` logs were emitted through. Same for the state reader.
* **A revert is a fact about the pool, so it needs a quorum too.** `call_answer`
  makes two endpoints agree that a call reverted, and on the payload where they
  send one. A refusal recorded on one node's word would be exactly the kind of
  single-source claim the pool in `evm.py` exists to prevent.
* **A refused size says nothing about another size.** So the capture is a
  ladder, not a probe: each pool is quoted at four sizes, and each answer --
  amount or refusal -- is recorded against the size it belongs to.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.v4_quote_capture
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from channelflow.dex.uniswap_v4 import PoolKey, ReconstructionClass, classify, pool_id
from tools.record.evm import (
    Answer,
    EndpointPool,
    address,
    encode_address,
    encode_uint,
    selector,
    signed,
    word,
)

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "uniswap_v4"

RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://1rpc.io/eth",
    "https://eth.merkle.io",
    "https://rpc.mevblocker.io",
    "https://gateway.tenderly.co/public/mainnet",
)

CHAIN_ID = 1

#: Candidates, not authorities. Each is verified against the manager below.
QUOTER = "0x52f0e24d1c21c8a0cb1e5a5dd6198556bd9e1203"
STATE_VIEW = "0x7ffe42c4a5deea5b0fec41c94c136cf115597227"

CONFIRMATIONS = 12

QUOTE_EXACT_INPUT_SINGLE = (
    "quoteExactInputSingle(((address,address,uint24,int24,address),bool,uint128,bytes))"
)

#: The ladder, in wei. Four sizes spanning three orders of magnitude, because
#: the interesting answer is where along it a pool stops being quotable.
SIZES = (10**15, 10**16, 10**17, 10**18)

#: The rung whose output seeds the reverse-direction quote, so the pair is a
#: round trip of a real amount rather than of a number picked here.
ROUND_TRIP_FROM = 10**16


def _encode_quote(key: PoolKey, *, zero_for_one: bool, exact_amount: int) -> str:
    """`QuoteExactSingleParams`: a `PoolKey`, a direction, a size, and hook data.

    The struct holds a `bytes` member, so it is dynamic and the call data opens
    with an offset to it. The `PoolKey` is static and inlines as five words.
    """
    body = (
        encode_address(key.currency0)
        + encode_address(key.currency1)
        + encode_uint(key.fee)
        + encode_uint(key.tick_spacing)
        + encode_address(key.hooks)
        + encode_uint(1 if zero_for_one else 0)
        + encode_uint(exact_amount)
        + encode_uint(8 * 32)  # offset to hookData, from the start of the tuple
        + encode_uint(0)  # hookData length: empty
    )
    return selector(QUOTE_EXACT_INPUT_SINGLE) + encode_uint(32) + body


def _verify_names_manager(pool: EndpointPool, contract: str, manager: str, block: str) -> None:
    named = address(pool.call(contract, selector("poolManager()"), block))
    if named.lower() != manager.lower():
        raise SystemExit(f"{contract} names manager {named}, not {manager}")


def _custom_accounting_pools(lines: list[str]) -> tuple[str, list[dict[str, Any]]]:
    manager = ""
    pools = []
    for line in lines:
        record = json.loads(line)
        if record.get("kind") == "manager":
            manager = record["manager"]
        if record.get("kind") != "pool":
            continue
        key = PoolKey(
            record["currency0"],
            record["currency1"],
            record["fee"],
            record["tick_spacing"],
            record["hooks"],
        )
        if classify(key) is not ReconstructionClass.CUSTOM_ACCOUNTING:
            continue
        derived = pool_id(key)
        if derived != record["pool_id"]:
            raise SystemExit(f"pool id {record['pool_id']} does not derive from its key")
        pools.append({"key": key, "pool_id": derived})
    if not manager:
        raise SystemExit("fixture carries no manager record")
    return manager, pools


def _quote_record(pool_id_hex: str, *, zero_for_one: bool, size: int, answer: Answer) -> dict:
    common = {
        "pool_id": pool_id_hex,
        "zero_for_one": zero_for_one,
        "exact_amount": str(size),
    }
    if answer.reverted:
        return {"kind": "refusal", **common, "revert_data": answer.revert_data}
    returned = answer.returned or ""
    return {
        "kind": "quote",
        **common,
        "amount_out": str(word(returned, 0)),
        "gas_estimate": word(returned, 1),
    }


def main() -> None:
    lines = (FIXTURES / "initialize.jsonl").read_text().splitlines()
    manager, pools = _custom_accounting_pools(lines)
    if not pools:
        raise SystemExit("no CUSTOM_ACCOUNTING pools in the fixture")

    endpoints = EndpointPool(RPCS)
    head = int(endpoints.any_rpc("eth_blockNumber", []), 16) - CONFIRMATIONS
    block = hex(head)
    print(f"{len(pools)} CUSTOM_ACCOUNTING pools, at block {head}")

    _verify_names_manager(endpoints, QUOTER, manager, block)
    _verify_names_manager(endpoints, STATE_VIEW, manager, block)
    print(f"quoter {QUOTER} and state view {STATE_VIEW} both name {manager}")

    out: list[dict[str, Any]] = [
        {
            "kind": "quoter",
            "chain_id": CHAIN_ID,
            "block": head,
            "pool_manager": manager,
            "quoter": QUOTER,
            "state_view": STATE_VIEW,
        }
    ]

    slot0 = selector("getSlot0(bytes32)")
    liquidity = selector("getLiquidity(bytes32)")
    for entry in pools:
        key: PoolKey = entry["key"]
        pid: str = entry["pool_id"]
        state = endpoints.call(STATE_VIEW, slot0 + pid[2:], block)
        out.append(
            {
                "kind": "state",
                "pool_id": pid,
                "currency0": key.currency0,
                "currency1": key.currency1,
                "fee": key.fee,
                "tick_spacing": key.tick_spacing,
                "hooks": key.hooks,
                "sqrt_price_x96": str(word(state, 0)),
                "tick": signed(state, 1),
                "protocol_fee": word(state, 2),
                "lp_fee": word(state, 3),
                "liquidity": str(word(endpoints.call(STATE_VIEW, liquidity + pid[2:], block))),
            }
        )

        round_trip: int | None = None
        for size in SIZES:
            answer = endpoints.call_answer(
                QUOTER, _encode_quote(key, zero_for_one=True, exact_amount=size), block
            )
            record = _quote_record(pid, zero_for_one=True, size=size, answer=answer)
            out.append(record)
            if size == ROUND_TRIP_FROM and record["kind"] == "quote":
                round_trip = int(record["amount_out"])
            said = record.get("amount_out") or record.get("revert_data")
            print(f"  {pid[:12]}… {size:>19} in -> {said}")

        if round_trip:
            answer = endpoints.call_answer(
                QUOTER,
                _encode_quote(key, zero_for_one=False, exact_amount=round_trip),
                block,
            )
            out.append(_quote_record(pid, zero_for_one=False, size=round_trip, answer=answer))
            print(f"  {pid[:12]}… round trip back from {round_trip}")

    path = FIXTURES / "quotes.jsonl"
    path.write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in out))
    print(f"wrote {len(out)} records to {path}")


if __name__ == "__main__":
    main()
