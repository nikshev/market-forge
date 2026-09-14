"""A `ChainDataProvider` that answers from a captured fixture (REQ-WP-071).

This is the replay seam. It is deliberately *below* the call encoder rather than
above it: the adapter builds its own call data, this looks that data up, and a
miss is a loud failure rather than a different-but-plausible number. An encoder
that sign-extended `int24 tickSpacing` wrongly would miss here; a replay that
answered decoded quotes would not notice at all.

It never returns `"0x"`. Empty return data decodes to `amount_out = 0`, and zero
is the one answer [[REQ-WP-071]] exists to forbid.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from channelflow.chain.providers import CallReverted
from channelflow.dex.uniswap_v4 import PoolKey
from channelflow.dex.v4_quoting import (
    POOL_MANAGER_SELECTOR,
    encode_exact_input_single,
)


class QuoteNotCaptured(LookupError):
    """The fixture holds no answer for this call.

    Raised rather than returning empty data. Nothing in production can raise
    this -- it exists so that a test which asks a question the chain was never
    asked fails, instead of silently being told zero.
    """


class ReplayProvider:
    """Answers `eth_call` from `tests/fixtures/uniswap_v4/quotes.jsonl`."""

    name = "replay"

    def __init__(self, path: Path) -> None:
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        header = next(row for row in rows if row["kind"] == "quoter")
        self.block: int = header["block"]
        self.chain_id: int = header["chain_id"]
        self.pool_manager: str = header["pool_manager"]
        self.quoter: str = header["quoter"]
        self.state_view: str = header["state_view"]
        self.states: dict[str, dict[str, Any]] = {
            row["pool_id"]: row for row in rows if row["kind"] == "state"
        }
        #: Every call the adapter has made, in order: (to, data, block).
        self.calls: list[tuple[str, str, int]] = []

        self._answers: dict[tuple[str, str], str] = {}
        self._reverts: dict[tuple[str, str], str] = {}
        for row in rows:
            if row["kind"] not in {"quote", "refusal"}:
                continue
            key = self._key(row)
            if row["kind"] == "quote":
                self._answers[key] = (
                    "0x" + f"{int(row['amount_out']):064x}" + f"{int(row['gas_estimate']):064x}"
                )
            else:
                self._reverts[key] = row["revert_data"]

    def _key(self, row: dict[str, Any]) -> tuple[str, str]:
        state = self.states[row["pool_id"]]
        key = PoolKey(
            state["currency0"],
            state["currency1"],
            state["fee"],
            state["tick_spacing"],
            state["hooks"],
        )
        data = encode_exact_input_single(
            key,
            zero_for_one=row["zero_for_one"],
            exact_amount=int(row["exact_amount"]),
        )
        return (self.quoter.lower(), data)

    def get_block(self, number: int) -> dict[str, Any]:
        raise NotImplementedError("the fixture holds no blocks")

    def get_logs(self, *, from_block: int, to_block: int) -> list[dict[str, Any]]:
        raise NotImplementedError("the fixture holds no logs")

    def eth_call(self, *, to: str, data: str, block: int) -> str:
        self.calls.append((to.lower(), data, block))
        lookup = (to.lower(), data)
        if data == POOL_MANAGER_SELECTOR and to.lower() in {
            self.quoter.lower(),
            self.state_view.lower(),
        }:
            # Stored decoded in the header: the capture verified both contracts
            # name this manager before recording anything.
            return "0x" + f"{int(self.pool_manager, 16):064x}"
        if lookup in self._reverts:
            raise CallReverted("the pool refused", self._reverts[lookup])
        if lookup in self._answers:
            return self._answers[lookup]
        raise QuoteNotCaptured(f"no capture for {to} {data[:10]}… at block {block}")
