"""One-shot recorder for Bybit v5 sample traffic.

# @trace: REQ-WP-043

PRD section 35.6 requires connector tests to replay exchange sample messages,
and [[ADR-004]] decided those samples are recorded from the real venue rather
than written from documentation: a live message carries fields older docs do not
mention, and a hand-written sample encodes the author's misunderstanding as a
passing test.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.bybit_capture

Writes newline-delimited JSON under tests/fixtures/bybit/. Those files are
committed and are the only thing the connector tests read. No credentials and no
account; every endpoint here is public, which is why this venue was picked.

**The product is linear perpetuals** (PRD section 5.2: "Bybit linear perps"),
not spot. The two streams differ in more than a URL -- a linear trade carries a
price-change direction field that spot does not -- so capturing the wrong one
would produce a connector for a market this project's universe does not include.

Endpoints and message shapes from the documentation the PRD's own reference list
names: https://bybit-exchange.github.io/docs/v5/ws/connect and
.../websocket/public/trade and .../websocket/public/orderbook.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "bybit"

LINEAR_WS = "wss://stream.bybit.com/v5/public/linear"

#: `orderbook.50` rather than `.1`: PRD section 11.1's reconstruction rules need
#: a snapshot and several deltas to say anything, and level 1 repeats an
#: unchanged snapshot every three seconds, which tests nothing.
TOPICS = ["publicTrade.BTCUSDT", "orderbook.50.BTCUSDT"]

#: Enough deltas to show sequence continuity across messages.
WANTED = {"publicTrade.BTCUSDT": 20, "orderbook.50.BTCUSDT": 40}

#: The documentation asks for a ping every 20 seconds. Sent at 15 so a slow
#: capture does not lose the connection mid-run and record a short file that
#: looks like a quiet market.
PING_SECONDS = 15

REST = {
    "rest_linear_instruments": (
        "https://api.bybit.com/v5/market/instruments-info?category=linear&symbol=BTCUSDT"
    ),
    "rest_linear_tickers": (
        "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
    ),
    "rest_linear_funding_history": (
        "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=3"
    ),
    "rest_linear_orderbook": (
        "https://api.bybit.com/v5/market/orderbook?category=linear&symbol=BTCUSDT&limit=5"
    ),
}


async def _capture(url: str, wanted: dict[str, int], seconds: int) -> dict[str, list[Any]]:
    got: dict[str, list[Any]] = {topic: [] for topic in wanted}
    deadline = time.monotonic() + seconds
    next_ping = time.monotonic() + PING_SECONDS

    async with websockets.connect(url, open_timeout=20) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": list(wanted)}))
        while time.monotonic() < deadline:
            if all(len(got[t]) >= n for t, n in wanted.items()):
                break
            if time.monotonic() >= next_ping:
                await ws.send(json.dumps({"op": "ping"}))
                next_ping = time.monotonic() + PING_SECONDS
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except TimeoutError:
                continue
            message = json.loads(raw)
            topic = message.get("topic")
            # The subscribe acknowledgement and pongs have no topic. Kept out of
            # the fixtures deliberately: they are connection lifecycle, and a
            # normaliser that had to skip them would be testing the recorder.
            if topic in got and len(got[topic]) < wanted[topic]:
                got[topic].append(message)
    return got


def _write(name: str, records: list[Any]) -> None:
    path = FIXTURES / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"  {path.name}: {len(records)}")


def main() -> None:
    print("linear streams")
    for topic, records in asyncio.run(_capture(LINEAR_WS, WANTED, 60)).items():
        _write("linear_" + topic.replace(".", "_").lower(), records)

    print("linear REST")
    for name, url in REST.items():
        with urllib.request.urlopen(url, timeout=20) as response:  # noqa: S310
            _write(name, [json.loads(response.read())])


if __name__ == "__main__":
    main()
