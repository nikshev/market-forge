"""One-shot recorder for each venue's funding history, so the interval is data.

# @trace: REQ-WP-050

Cross-venue funding dispersion is meaningless unless the rates cover the same
period, and the periods differ: measured on 2026-09-12, Hyperliquid settles
hourly and Binance, Bybit and OKX every eight hours. A dispersion over the raw
rates measures the settlement schedule.

So the fixture records **history**, not a stated interval. The gap between
consecutive settlements is then derived by the tests from the venue's own
timestamps, which is the difference between an assertion and a claim.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.funding_history_capture

Writes newline-delimited JSON under tests/fixtures/derivatives/. No credentials:
every endpoint here is public.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "derivatives"

HEADERS = {"User-Agent": "channelflow-capture/1.0", "Content-Type": "application/json"}
PAUSE_SECONDS = 0.4

#: Two days, which is enough to see the gap repeat rather than to see it once.
LOOKBACK_MS = 2 * 24 * 60 * 60 * 1000


def _request(url: str, body: dict[str, Any] | None = None) -> Any:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers=HEADERS)  # noqa: S310
    with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
        result = json.load(response)
    time.sleep(PAUSE_SECONDS)
    return result


def main() -> None:
    now_ms = int(time.time() * 1000)
    rows: list[dict[str, Any]] = []

    binance = _request("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=20")
    rows.append(
        {
            "kind": "funding_history",
            "venue": "binance",
            "symbol": "BTCUSDT",
            "settlements": [
                {"time_ms": int(entry["fundingTime"]), "rate": entry["fundingRate"]}
                for entry in binance
            ],
        }
    )

    bybit = _request(
        "https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=20"
    )["result"]["list"]
    rows.append(
        {
            "kind": "funding_history",
            "venue": "bybit",
            "symbol": "BTCUSDT",
            "settlements": [
                {"time_ms": int(entry["fundingRateTimestamp"]), "rate": entry["fundingRate"]}
                for entry in bybit
            ],
        }
    )

    okx = _request(
        "https://www.okx.com/api/v5/public/funding-rate-history?instId=BTC-USDT-SWAP&limit=20"
    )["data"]
    rows.append(
        {
            "kind": "funding_history",
            "venue": "okx",
            "symbol": "BTC-USDT-SWAP",
            "settlements": [
                {"time_ms": int(entry["fundingTime"]), "rate": entry["realizedRate"]}
                for entry in okx
            ],
        }
    )

    hyperliquid = _request(
        "https://api.hyperliquid.xyz/info",
        {"type": "fundingHistory", "coin": "BTC", "startTime": now_ms - LOOKBACK_MS},
    )
    rows.append(
        {
            "kind": "funding_history",
            "venue": "hyperliquid",
            "symbol": "BTC",
            "settlements": [
                {"time_ms": int(entry["time"]), "rate": entry["fundingRate"]}
                for entry in hyperliquid
            ],
        }
    )

    for row in rows:
        stamps = sorted(entry["time_ms"] for entry in row["settlements"])
        # Rounded, not truncated. Hyperliquid's settlements carry a couple of
        # milliseconds of jitter, and integer division turns 59.998 minutes into
        # "59" -- which reads as a venue that settles just under the hour.
        gaps = sorted(
            {round((b - a) / 60_000, 3) for a, b in zip(stamps, stamps[1:], strict=False)}
        )
        print(f"  {row['venue']:>12}: {len(stamps):>3} settlements, gaps {gaps} minutes")

    rows.insert(0, {"kind": "capture", "captured_ms": now_ms})
    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "funding_history.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    )
    print(f"  {path.name}: {len(rows)}")


if __name__ == "__main__":
    main()
