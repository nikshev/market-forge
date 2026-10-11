"""One public HTTP GET, and what each way it can go wrong becomes.

# @trace: REQ-WP-093

A poll that fails must store nothing (spec 145, FR-004), so every failure here is an exception the
caller can name and count, and none of them is a half-answer: a timeout, a refused connection, a
non-success status and an answer that is not JSON are all `RestFailure`, and a rate limit is the
subclass that says how long the venue asked us to wait. Nothing here retries; the loop decides when
the next attempt is, because it knows the cadence and this does not.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

import httpx

#: Used when a rate-limited answer does not say how long to wait. A minute: the poll cadence, so a
#: venue that throttles us is asked once more per cycle at most and never in a tight loop.
DEFAULT_RETRY_AFTER_S = 60.0

#: Binance answers 418 when an IP that kept hitting a 429 has been banned, with the ban's length in
#: `Retry-After`; it is a rate limit that has got worse and is treated as one.
RATE_LIMIT_STATUSES = frozenset({429, 418})


class RestFailure(Exception):
    """A request that produced no usable answer. `endpoint` names it; `reason` says why."""

    def __init__(self, endpoint: str, reason: str) -> None:
        super().__init__(f"{endpoint}: {reason}")
        self.endpoint = endpoint
        self.reason = reason


class RateLimited(RestFailure):
    """The venue asked us to slow down, and how long to wait."""

    def __init__(self, endpoint: str, retry_after_s: float) -> None:
        super().__init__(endpoint, f"rate limited, retry after {retry_after_s:g}s")
        self.retry_after_s = retry_after_s


class JsonClient(Protocol):
    def get(self, url: str, params: Mapping[str, str] | None = None) -> Any: ...


class HttpxJsonClient:
    """`JsonClient` over httpx, with a timeout on everything and no retry."""

    def __init__(
        self, *, timeout: float = 10.0, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._client = httpx.Client(timeout=timeout, transport=transport)

    def get(self, url: str, params: Mapping[str, str] | None = None) -> Any:
        try:
            response = self._client.get(url, params=dict(params or {}))
        except httpx.HTTPError as exc:
            raise RestFailure(url, f"{type(exc).__name__}: {exc}") from exc
        if response.status_code in RATE_LIMIT_STATUSES:
            raise RateLimited(url, _retry_after(response))
        if response.status_code != 200:
            raise RestFailure(url, f"HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise RestFailure(url, "the answer is not JSON") from exc

    def close(self) -> None:
        self._client.close()


def _retry_after(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After")
    try:
        seconds = float(raw) if raw is not None else DEFAULT_RETRY_AFTER_S
    except ValueError:
        return DEFAULT_RETRY_AFTER_S
    return max(seconds, 0.0) if raw is not None else DEFAULT_RETRY_AFTER_S
