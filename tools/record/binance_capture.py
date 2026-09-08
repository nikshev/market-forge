"""One-shot recorder for Binance sample traffic.

# @trace: REQ-WP-003

PRD section 35.6 requires connector tests to replay exchange sample messages.
ADR-004 decided those samples are recorded from the real venue rather than
written from documentation -- a live depth message carries `ps` and `st` fields
that older docs do not mention, and a hand-written sample would have encoded
that misunderstanding.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.binance_capture

Writes newline-delimited JSON under tests/fixtures/binance/. Those files are
committed and are the only thing the connector tests read. No credentials; every
endpoint here is public.

**What this network can and cannot reach.** Verified before writing this:
spot websocket streams all deliver. On futures, `@depth` delivers but
`@aggTrade`, `@markPrice` and `@forceOrder` connect and stay silent -- a
regional or edge-routing limit, not a code fault. Mark price, index price,
funding and open interest are therefore taken from futures REST, which answers
normally. Liquidations are not captured at all; REQ-WP-003 asks for them "when
available from the venue", and here they are not.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "binance"

SPOT_WS = (
    "wss://stream.binance.com:9443/stream?streams="
    "btcusdt@aggTrade/btcusdt@trade/btcusdt@depth@100ms/btcusdt@bookTicker"
)
FUTURES_WS = "wss://fstream.binance.com/stream?streams=btcusdt@depth@100ms"

#: Enough depth updates to show sequence continuity across several messages,
#: which is what PRD section 11.1's reconstruction rules are tested against.
WANTED = {
    "btcusdt@aggTrade": 15,
    "btcusdt@trade": 15,
    "btcusdt@depth@100ms": 30,
    "btcusdt@bookTicker": 10,
}

REST = {
    "rest_futures_open_interest": "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT",
    "rest_futures_premium_index": "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
    "rest_futures_funding_rate": (
        "https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3"
    ),
    "rest_futures_depth_snapshot": (
        "https://fapi.binance.com/fapi/v1/depth?symbol=BTCUSDT&limit=5"
    ),
    "rest_spot_depth_snapshot": ("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=5"),
}


async def _capture(url: str, wanted: dict[str, int], seconds: int) -> dict[str, list[Any]]:
    got: dict[str, list[Any]] = {name: [] for name in wanted}
    deadline = time.monotonic() + seconds
    async with websockets.connect(url, open_timeout=20) as ws:
        while time.monotonic() < deadline:
            if all(len(got[s]) >= n for s, n in wanted.items()):
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except TimeoutError:
                continue
            message = json.loads(raw)
            stream = message.get("stream")
            if stream in got and len(got[stream]) < wanted[stream]:
                got[stream].append(message)
    return got


def _write(name: str, records: list[Any]) -> None:
    path = FIXTURES / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"  {path.name}: {len(records)}")


def main() -> None:
    print("spot streams")
    for stream, records in asyncio.run(_capture(SPOT_WS, WANTED, 30)).items():
        _write("spot_" + stream.replace("@", "_"), records)

    print("futures depth")
    futures = asyncio.run(_capture(FUTURES_WS, {"btcusdt@depth@100ms": 30}, 20))
    for stream, records in futures.items():
        _write("futures_" + stream.replace("@", "_"), records)

    print("futures REST")
    for name, url in REST.items():
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310
            _write(name, [json.loads(response.read())])


if __name__ == "__main__":
    main()
