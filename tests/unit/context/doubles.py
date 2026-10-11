"""Doubles for the collector's tests: a fake HTTP client over the recorded answers."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from channelflow.context.rest import RestFailure

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "context"


def load(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


#: The route (a substring of the URL path) each recorded answer belongs to.
ROUTES: dict[str, str] = {
    "/fapi/v1/premiumIndex": "binance_premiumIndex",
    "/futures/data/openInterestHist": "binance_openInterestHist",
    "/fapi/v1/fundingRate": "binance_fundingRate",
    "/v5/market/tickers": "bybit_tickers",
    "/v5/market/funding/history": "bybit_funding_history",
    "/api/v5/public/open-interest": "okx_open_interest",
    "/api/v5/public/funding-rate-history": "okx_funding_history",
    "/api/v5/public/funding-rate": "okx_funding_rate",
    "/api/v5/public/mark-price": "okx_mark_price",
    "/api/v5/market/index-tickers": "okx_index_tickers",
    "/api/v5/public/instruments": "okx_instruments",
}


class FakeClient:
    """Answers each endpoint with its recorded response, or fails the ones named in `fail`."""

    def __init__(self, fail: Mapping[str, Exception] | None = None) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.fail = dict(fail or {})

    def get(self, url: str, params: Mapping[str, str] | None = None) -> Any:
        self.calls.append((url, dict(params or {})))
        # Longest route first: `/funding-rate-history` contains `/funding-rate`.
        for route in sorted(ROUTES, key=len, reverse=True):
            if route in url:
                if route in self.fail:
                    raise self.fail[route]
                return load(ROUTES[route])
        raise RestFailure(url, "no recorded answer for this endpoint")
