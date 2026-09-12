"""One-shot recorder for Bybit and OKX public derivatives responses.

# @trace: REQ-WP-049

PRD section 35.6 requires connector tests to replay exchange sample messages,
and [[ADR-004]] decided those samples are recorded from the real venue rather
than written from documentation.

Run deliberately, never in CI:

    .venv/bin/python -m tools.record.derivatives_capture

Writes newline-delimited JSON under tests/fixtures/derivatives/. No credentials:
Bybit's `/v5/market/tickers` and OKX's `/api/v5/public/*` answer unsigned.

**Both venues are captured in one pass, as close together as the endpoints
allow.** The two disagree about units and about names, and the disagreements are
only demonstrable side by side:

* OKX reports open interest in *contracts* and Bybit in base units, so the same
  market read naively looks fifty times larger on one venue;
* `OKX.fundingTime` is `Bybit.nextFundingTime` -- the same instant under
  opposite names, eight hours from the field OKX calls `nextFundingTime`.

A fixture that recorded either venue alone could assert neither.

**OKX's instrument data is captured too, and it is not optional**, for the
reason `okx_capture.py` gives about trade size: the contract value differs per
instrument and can change, and a compiled-in number would be right until the day
it silently was not.

**The four OKX endpoints carry four timestamps**, and all of them are kept. An
OKX state is assembled from readings taken moments apart, and how far apart is a
fact about the state rather than noise to discard.

**The index price is captured rather than the venue's `premium`.** OKX's funding
response carries a `premium`, which looks like the mark-against-index basis and
is not: measured, the two are 0.14 basis points apart, because the premium is
averaged over a funding window and the basis is instantaneous. Using it would
mean comparing OKX's window against Bybit's instant under one name.

Endpoints from https://bybit-exchange.github.io/docs/v5/ and
https://www.okx.com/docs-v5/.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "derivatives"

HEADERS = {"User-Agent": "channelflow-capture/1.0"}
PAUSE_SECONDS = 0.4

#: One liquid perp per venue, plus a second pair so a test cannot pass by
#: assuming one instrument's contract value is every instrument's.
PAIRS = (
    ("BTCUSDT", "BTC-USDT-SWAP"),
    ("ETHUSDT", "ETH-USDT-SWAP"),
)

BYBIT_TICKERS = "https://api.bybit.com/v5/market/tickers?category=linear&symbol={symbol}"
OKX_FUNDING = "https://www.okx.com/api/v5/public/funding-rate?instId={inst}"
OKX_OPEN_INTEREST = "https://www.okx.com/api/v5/public/open-interest?instId={inst}"
OKX_MARK = "https://www.okx.com/api/v5/public/mark-price?instId={inst}"
OKX_INSTRUMENTS = "https://www.okx.com/api/v5/public/instruments?instType=SWAP&instId={inst}"
OKX_INDEX = "https://www.okx.com/api/v5/market/index-tickers?instId={underlying}"


def _get(url: str) -> Any:
    request = urllib.request.Request(url, headers=HEADERS)  # noqa: S310
    with urllib.request.urlopen(request, timeout=25) as response:  # noqa: S310
        body = json.load(response)
    time.sleep(PAUSE_SECONDS)
    return body


def main() -> None:
    started_ns = time.time_ns()
    rows: list[dict[str, Any]] = []

    for symbol, inst_id in PAIRS:
        bybit = _get(BYBIT_TICKERS.format(symbol=symbol))
        ticker = bybit["result"]["list"][0]
        rows.append(
            {
                "kind": "bybit_ticker",
                "symbol": symbol,
                "received_ns": time.time_ns(),
                "body": ticker,
            }
        )

        funding = _get(OKX_FUNDING.format(inst=inst_id))["data"][0]
        open_interest = _get(OKX_OPEN_INTEREST.format(inst=inst_id))["data"][0]
        mark = _get(OKX_MARK.format(inst=inst_id))["data"][0]
        instrument = _get(OKX_INSTRUMENTS.format(inst=inst_id))["data"][0]
        # The index instrument comes from the swap's own `uly`, not from
        # stripping "-SWAP" off its id: the venue says what it settles against,
        # and deriving it would be a guess that happens to work for these two.
        index = _get(OKX_INDEX.format(underlying=instrument["uly"]))["data"][0]
        rows.append(
            {
                "kind": "okx_derivatives",
                "inst_id": inst_id,
                "received_ns": time.time_ns(),
                "funding": funding,
                "open_interest": open_interest,
                "mark": mark,
                "index": index,
                "instrument": instrument,
            }
        )

        print(
            f"  {symbol:>9} bybit oi={ticker['openInterest']} funding={ticker['fundingRate']} "
            f"next={ticker['nextFundingTime']}"
        )
        print(
            f"  {inst_id:>15} okx oi={open_interest['oi']} (ccy {open_interest['oiCcy']}) "
            f"ctVal={instrument['ctVal']} fundingTime={funding['fundingTime']} "
            f"next={funding['nextFundingTime']}"
        )

    elapsed_ns = time.time_ns() - started_ns
    rows.insert(0, {"kind": "capture", "started_ns": started_ns, "elapsed_ns": elapsed_ns})
    print(f"one pass in {elapsed_ns / 1e9:.1f}s")

    FIXTURES.mkdir(parents=True, exist_ok=True)
    path = FIXTURES / "bybit_okx.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    )
    print(f"  {path.name}: {len(rows)}")


if __name__ == "__main__":
    main()
