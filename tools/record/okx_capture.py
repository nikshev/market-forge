"""One-shot recorder for OKX v5 sample traffic.

# @trace: REQ-WP-044

PRD section 35.6 requires connector tests to replay exchange sample messages,
and [[ADR-004]] decided those samples are recorded from the real venue rather
than written from documentation.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.okx_capture

Writes newline-delimited JSON under tests/fixtures/okx/. Those files are
committed and are the only thing the connector tests read. No credentials and no
account; every endpoint here is public.

**The instruments response is captured too, and it is not optional.** OKX quotes
trade size in *contracts*, and `BTC-USDT-SWAP` carries `ctVal = 0.01 BTC`. A
connector that read `sz` as a base quantity would report volumes a hundredfold
too large with no symptom, so the contract value has to come from the venue and
the fixture has to carry it.

**Trades and the book are captured on one connection**, deliberately. The
`side` field's meaning is not stated in any documentation page that renders, so
it is established from the recording: a taker's buy executes at the ask. That
only works if the two streams are recorded together and interleaved.

Endpoints and message shapes from https://www.okx.com/docs-v5/.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "okx"

PUBLIC_WS = "wss://ws.okx.com:8443/ws/v5/public"
INSTRUMENT = "BTC-USDT-SWAP"

#: `books` is the 400-level channel with a snapshot followed by deltas, which is
#: what PRD section 11.1's reconstruction rules need. `books5` would send a
#: fresh five-level snapshot every time and test nothing.
CHANNELS = [
    {"channel": "trades", "instId": INSTRUMENT},
    {"channel": "books", "instId": INSTRUMENT},
]

WANTED = {"trades": 40, "books": 40}

#: The documentation asks for a ping if nothing has arrived for 30 seconds. Sent
#: at 20 so a quiet market does not drop the connection mid-capture and leave a
#: short file that looks like a calm one.
PING_SECONDS = 20

#: A browser-ish agent: the REST host answers 403 to urllib's default.
REST_HEADERS = {"User-Agent": "channelflow-capture/1.0"}

REST = {
    "rest_swap_instruments": (
        f"https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={INSTRUMENT}"
    ),
    "rest_swap_orderbook": (f"https://www.okx.com/api/v5/market/books?instId={INSTRUMENT}&sz=5"),
}


async def _capture(seconds: int) -> tuple[dict[str, list[Any]], list[Any]]:
    """Records per channel, and the interleaved order they arrived in.

    The interleaving is what establishes what `side` means: a trade's side can
    only be checked against the book as it stood when the trade arrived, and a
    per-channel file loses that.
    """
    got: dict[str, list[Any]] = {name: [] for name in WANTED}
    stream: list[Any] = []
    deadline = time.monotonic() + seconds
    next_ping = time.monotonic() + PING_SECONDS

    async with websockets.connect(PUBLIC_WS, open_timeout=20) as ws:
        await ws.send(json.dumps({"op": "subscribe", "args": CHANNELS}))
        while time.monotonic() < deadline:
            if all(len(got[c]) >= n for c, n in WANTED.items()):
                break
            if time.monotonic() >= next_ping:
                await ws.send("ping")
                next_ping = time.monotonic() + PING_SECONDS
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except TimeoutError:
                continue
            if raw == "pong":
                continue
            message = json.loads(raw)
            # Subscribe acknowledgements have `event` and no `data`. Kept out of
            # the fixtures: they are connection lifecycle, and a normaliser that
            # had to skip them would be testing the recorder.
            channel = message.get("arg", {}).get("channel")
            if channel in got and "data" in message:
                stream.append(message)
                if len(got[channel]) < WANTED[channel]:
                    got[channel].append(message)
    return got, stream


def _write(name: str, records: list[Any]) -> None:
    path = FIXTURES / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"  {path.name}: {len(records)}")


def main() -> None:
    print("public streams")
    per_channel, stream = asyncio.run(_capture(90))
    for channel, records in per_channel.items():
        _write(f"swap_{channel}", records)
    _write("swap_interleaved", stream)

    print("public REST")
    for name, url in REST.items():
        request = urllib.request.Request(url, headers=REST_HEADERS)  # noqa: S310
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310
            _write(name, [json.loads(response.read())])


if __name__ == "__main__":
    main()
