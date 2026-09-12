"""One-shot recorder for HyperCore's public `info` responses.

# @trace: REQ-WP-048

PRD section 35.6 requires connector tests to replay exchange sample messages,
and [[ADR-004]] decided those samples are recorded from the real venue rather
than written from documentation.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.hypercore_capture

Writes newline-delimited JSON under tests/fixtures/hypercore/. No credentials
and no account: Hyperliquid's `info` endpoint answers unsigned POST requests,
which is the only reason this venue is reachable under the constraint that no
KYC is involved.

**The metadata responses are captured too, and they are not optional.** Section
18.25 asks for "market symbol normalization", and on this venue that is the
substance rather than a detail:

* `allMids` keys arrive in three shapes -- bare, `@`-prefixed and `#`-prefixed
  -- and a key is not a symbol until something says which;
* `meta.universe` keeps delisted assets **at their indices**, so a mapping that
  enumerates only what is still listed drifts further wrong the further down the
  list it goes;
* `spotMeta.universe` is sparse in the opposite direction -- a pair's `index` is
  not its position -- so one venue carries two index conventions that fail in
  opposite ways.

Capturing `meta` and `spotMeta` alongside `allMids` is what lets a test assert
all of that instead of a docstring claiming it.

**Trades and the book are captured on one connection**, deliberately and for the
same reason the OKX capture is. A trade's `side` is `"B"` or `"A"`, which could
be the taker's direction or the resting side it hit, and no documentation page
settles it. Interleaved with the book, it settles itself: a taker's buy executes
at the ask. That only works if the two streams share a connection and a clock.

**Everything else is captured in one pass, as close together as the API allows**, and
the capture records how long the pass took. `allMids` and `spotMeta` are not a
consistent snapshot of each other -- keys in one resolve against nothing in the
other -- and a fixture that hid the gap would test a venue that does not exist.

Endpoints from https://hyperliquid.gitbook.io/hyperliquid-docs/.
"""

from __future__ import annotations

import asyncio
import json
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "hypercore"

INFO_URL = "https://api.hyperliquid.xyz/info"
WS_URL = "wss://api.hyperliquid.xyz/ws"
HEADERS = {"Content-Type": "application/json", "User-Agent": "channelflow-capture/1.0"}

#: A breath between calls. The endpoint is public and unmetered, and a tool that
#: ignored that would be taking from a commons to save itself a few seconds.
PAUSE_SECONDS = 0.4

#: How long to hold the socket open, and how many trades are enough to settle
#: what `side` means. A handful would not: the question is answered by a
#: majority across trades that arrive between book updates.
WS_SECONDS = 120
TRADES_WANTED = 60

#: Books to capture. BTC for depth, and a thinner asset so a test cannot pass by
#: assuming every book has hundreds of levels.
BOOK_COINS = ("BTC", "ETH", "PURR/USDC")


def _info(body: dict[str, Any]) -> Any:
    request = urllib.request.Request(  # noqa: S310
        INFO_URL, data=json.dumps(body).encode(), headers=HEADERS
    )
    with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
        result = json.load(response)
    time.sleep(PAUSE_SECONDS)
    return result


async def _stream(coin: str) -> list[dict[str, Any]]:
    """One connection, trades and book together, in arrival order.

    Arrival order is the whole point. Separated, the two streams cannot answer
    what `side` means; interleaved, a taker's buy is visibly the one that
    executes at the ask.
    """
    captured: list[dict[str, Any]] = []
    trades = 0
    async with websockets.connect(WS_URL, open_timeout=20) as socket:
        for subscription in ({"type": "trades", "coin": coin}, {"type": "bbo", "coin": coin}):
            await socket.send(json.dumps({"method": "subscribe", "subscription": subscription}))
        deadline = time.monotonic() + WS_SECONDS
        while time.monotonic() < deadline and trades < TRADES_WANTED:
            try:
                raw = await asyncio.wait_for(socket.recv(), timeout=15)
            except TimeoutError:
                break
            message = json.loads(raw)
            if message.get("channel") not in {"trades", "bbo"}:
                continue
            captured.append({"received_ns": time.time_ns(), "message": message})
            if message["channel"] == "trades":
                trades += len(message["data"])
    print(f"  {coin}: {len(captured)} messages, {trades} trades")
    return captured


def main() -> None:
    started_ns = time.time_ns()
    rows: list[dict[str, Any]] = []

    meta = _info({"type": "meta"})
    rows.append({"kind": "meta", "body": meta})
    universe = meta["universe"]
    delisted = [index for index, asset in enumerate(universe) if asset.get("isDelisted")]
    print(f"meta: {len(universe)} perps, {len(delisted)} delisted, first at index {delisted[:3]}")

    spot_meta = _info({"type": "spotMeta"})
    rows.append({"kind": "spotMeta", "body": spot_meta})
    indices = [pair["index"] for pair in spot_meta["universe"]]
    print(
        f"spotMeta: {len(indices)} pairs, indices to {max(indices)}, "
        f"{len(spot_meta['tokens'])} tokens"
    )

    mids = _info({"type": "allMids"})
    rows.append({"kind": "allMids", "body": mids})
    shapes = {"bare": 0, "@": 0, "#": 0}
    for key in mids:
        shapes["@" if key.startswith("@") else "#" if key.startswith("#") else "bare"] += 1
    print(f"allMids: {len(mids)} keys {shapes}")

    contexts = _info({"type": "metaAndAssetCtxs"})
    rows.append({"kind": "metaAndAssetCtxs", "body": contexts})
    print(f"metaAndAssetCtxs: {len(contexts[1])} contexts")

    dexes = _info({"type": "perpDexs"})
    rows.append({"kind": "perpDexs", "body": dexes})
    print(f"perpDexs: {[(entry or {}).get('name', '<main>') for entry in dexes]}")

    for coin in BOOK_COINS:
        book = _info({"type": "l2Book", "coin": coin})
        rows.append({"kind": "l2Book", "coin": coin, "body": book})
        bids, asks = book["levels"]
        print(f"l2Book {coin}: {len(bids)} bids, {len(asks)} asks at {book['time']}")

    print("streaming trades and quotes together")
    for coin in ("BTC", "ETH"):
        for entry in asyncio.run(_stream(coin)):
            rows.append({"kind": "stream", "coin": coin, **entry})

    elapsed_ns = time.time_ns() - started_ns
    rows.insert(
        0,
        {
            "kind": "capture",
            "started_ns": started_ns,
            "elapsed_ns": elapsed_ns,
            "endpoint": INFO_URL,
        },
    )
    print(f"one pass in {elapsed_ns / 1e9:.1f}s")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "info.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    )
    print(f"  {path.name}: {len(rows)} ({path.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
