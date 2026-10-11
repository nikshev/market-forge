"""Each venue's derivatives poll and settled-funding history, as states (REQ-WP-093).

# @trace: REQ-WP-093

A poller does what a venue's public REST API lets it and turns the answers into `DerivativesState`
rows with the project's normalizers; it decides nothing about cadence, storage or health. Two
rules shape every method here:

* **A poll with one failing request returns nothing.** The venue's answers are separate calls, and a
  state assembled from the ones that worked would carry a mark price with a funding rate from before
  the failure. `PollFailed` (or `RateLimited`, which also says how long to wait) leaves the caller
  with the previous state *in the table* and nothing new, which is the honest picture of a poll that
  did not happen.
* **Nothing is defaulted.** A field the venue did not send is absent in the state; the normalizers
  refuse an answer missing a field they require, naming it.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any, Protocol

from channelflow.connectors.binance import normalize as binance
from channelflow.connectors.bybit import normalize as bybit
from channelflow.connectors.okx import normalize as okx
from channelflow.context.rest import JsonClient, RateLimited, RestFailure
from channelflow.domain import DerivativesState

MS_TO_NS = 1_000_000

#: How many settlements each history request asks for: enough for `funding_z`'s 24 with a margin,
#: and no venue's cap is lower.
HISTORY_LIMIT = 50

#: The Binance open-interest buckets read per poll. Three covers a restart or a missed poll;
#: re-reading one already stored is dropped by the sink.
BINANCE_OI_BUCKETS = 3

#: How far apart OKX's four readings of one state may be before it is refused as not one instant.
OKX_MAX_SPREAD_NS = 30_000_000_000


class PollFailed(Exception):
    """A poll or a history load that did not complete; the message names the request."""


class Poller(Protocol):
    venue: str

    def poll(self, symbol: str) -> list[DerivativesState]: ...

    def history(self, symbol: str) -> list[DerivativesState]: ...


def _get(client: JsonClient, url: str, params: dict[str, str]) -> Any:
    try:
        return client.get(url, params)
    except RateLimited:
        raise
    except RestFailure as exc:
        raise PollFailed(f"{exc.endpoint}: {exc.reason}") from exc


def _normalizing(what: str, action: Callable[[], Any]) -> Any:
    """Run a normalizer; any way the answer is not what it should be is a failed poll.

    `NormalizationError` and pydantic's validation error are both `ValueError`; a missing key or an
    answer of the wrong shape is a `KeyError`, `TypeError` or `IndexError`. All of them mean the
    same thing to the caller -- this poll produced nothing -- and none is worth a stack trace.
    """
    try:
        return action()
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise PollFailed(f"{what}: {type(exc).__name__}: {exc}") from exc


class BinancePoller:
    venue = "binance"
    BASE = "https://fapi.binance.com"

    def __init__(self, client: JsonClient, now_ns: Callable[[], int]) -> None:
        self._client = client
        self._now = now_ns

    def poll(self, symbol: str) -> list[DerivativesState]:
        premium = _get(self._client, f"{self.BASE}/fapi/v1/premiumIndex", {"symbol": symbol})
        buckets = _get(
            self._client,
            f"{self.BASE}/futures/data/openInterestHist",
            {"symbol": symbol, "period": "5m", "limit": str(BINANCE_OI_BUCKETS)},
        )
        now = self._now()
        states: list[DerivativesState] = [
            _normalizing(
                "premiumIndex",
                lambda: binance.futures_state(premium, venue=self.venue, ingest_time_ns=now),
            )
        ]
        states.extend(
            _normalizing(
                "openInterestHist",
                lambda row=row: binance.open_interest_state(  # type: ignore[misc]
                    row, venue=self.venue, ingest_time_ns=now
                ),
            )
            for row in buckets
        )
        return states

    def history(self, symbol: str) -> list[DerivativesState]:
        rows = _get(
            self._client,
            f"{self.BASE}/fapi/v1/fundingRate",
            {"symbol": symbol, "limit": str(HISTORY_LIMIT)},
        )
        now = self._now()
        return list(
            _normalizing(
                "fundingRate",
                lambda: binance.funding_history(rows, venue=self.venue, ingest_time_ns=now),
            )
        )


class BybitPoller:
    venue = "bybit"
    BASE = "https://api.bybit.com"

    def __init__(self, client: JsonClient, now_ns: Callable[[], int]) -> None:
        self._client = client
        self._now = now_ns

    def poll(self, symbol: str) -> list[DerivativesState]:
        body = _get(
            self._client,
            f"{self.BASE}/v5/market/tickers",
            {"category": "linear", "symbol": symbol},
        )
        now = self._now()

        def build() -> DerivativesState:
            rows = body["result"]["list"]
            if not rows:
                raise bybit.NormalizationError(f"tickers: no row for {symbol}")
            return bybit.derivatives_state(
                rows[0],
                venue=self.venue,
                market_type="perp",
                ingest_time_ns=now,
                event_time_ns=int(body["time"]) * MS_TO_NS,
            )

        return [_normalizing("tickers", build)]

    def history(self, symbol: str) -> list[DerivativesState]:
        body = _get(
            self._client,
            f"{self.BASE}/v5/market/funding/history",
            {"category": "linear", "symbol": symbol, "limit": str(HISTORY_LIMIT)},
        )
        now = self._now()
        return list(
            _normalizing(
                "funding/history",
                lambda: bybit.funding_history(
                    body["result"]["list"], venue=self.venue, market_type="perp", ingest_time_ns=now
                ),
            )
        )


class OkxPoller:
    venue = "okx"
    BASE = "https://www.okx.com"

    def __init__(self, client: JsonClient, now_ns: Callable[[], int]) -> None:
        self._client = client
        self._now = now_ns
        self._contract_values: dict[str, Decimal] = {}

    def _data(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        body = _get(self._client, f"{self.BASE}{path}", params)
        if body.get("code") != "0" or not body.get("data"):
            raise PollFailed(f"{path}: code {body.get('code')!r}, msg {body.get('msg')!r}")
        return dict(body["data"][0])

    def _contract_value(self, symbol: str) -> Decimal:
        if symbol not in self._contract_values:
            body = _get(
                self._client,
                f"{self.BASE}/api/v5/public/instruments",
                {"instType": "SWAP", "instId": symbol},
            )
            self._contract_values[symbol] = _normalizing(
                "instruments", lambda: okx.contract_value(body, inst_id=symbol)
            )
        return self._contract_values[symbol]

    def poll(self, symbol: str) -> list[DerivativesState]:
        contract_value = self._contract_value(symbol)
        funding = self._data("/api/v5/public/funding-rate", {"instId": symbol})
        interest = self._data(
            "/api/v5/public/open-interest", {"instType": "SWAP", "instId": symbol}
        )
        mark = self._data("/api/v5/public/mark-price", {"instType": "SWAP", "instId": symbol})
        # The index ticker is asked for by the underlying (BTC-USDT), not the swap's own name.
        index = self._data("/api/v5/market/index-tickers", {"instId": symbol.removesuffix("-SWAP")})
        now = self._now()
        assembled = _normalizing(
            "derivatives",
            lambda: okx.derivatives_state(
                funding=funding,
                open_interest=interest,
                mark=mark,
                index=index,
                contract_value=contract_value,
                venue=self.venue,
                market_type="perp",
                ingest_time_ns=now,
                max_spread_ns=OKX_MAX_SPREAD_NS,
            ),
        )
        return [assembled.state]

    def history(self, symbol: str) -> list[DerivativesState]:
        body = _get(
            self._client,
            f"{self.BASE}/api/v5/public/funding-rate-history",
            {"instId": symbol, "limit": str(HISTORY_LIMIT)},
        )
        if body.get("code") != "0":
            raise PollFailed(f"funding-rate-history: code {body.get('code')!r}")
        now = self._now()
        return list(
            _normalizing(
                "funding-rate-history",
                lambda: okx.funding_history(
                    body["data"], venue=self.venue, market_type="perp", ingest_time_ns=now
                ),
            )
        )


_POLLERS: dict[str, Callable[[JsonClient, Callable[[], int]], Poller]] = {
    "binance": BinancePoller,
    "bybit": BybitPoller,
    "okx": OkxPoller,
}


def poller_for(venue: str, client: JsonClient, now_ns: Callable[[], int]) -> Poller:
    try:
        return _POLLERS[venue](client, now_ns)
    except KeyError:
        raise ValueError(
            f"no poller for venue {venue!r}; known: {', '.join(sorted(_POLLERS))}"
        ) from None
