"""The collector's loop: what is due when, and what a failure does to it (REQ-WP-093).

# @trace: REQ-WP-093

`Collector.step` does everything that is due at the instant it is given and returns; it never
sleeps and never reads a clock of its own, so a test drives it on a counter and the real loop is
three lines around it. A failure is local to what failed: a poll that did not complete stores
nothing and is tried again next cycle, a rate limit waits as long as the venue asked, a commit that
failed keeps its rows for the next one -- and none of it can stop the loop, because the thing worse
than a failed poll is a collector that is no longer asking.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from channelflow.context import sources
from channelflow.context.pollers import Poller, PollFailed
from channelflow.context.rest import RateLimited
from channelflow.context.status import Status
from channelflow.domain import DerivativesState

logger = logging.getLogger(__name__)

SECOND_NS = 1_000_000_000


class StateSink(Protocol):
    def __call__(self, state: DerivativesState) -> None: ...

    @property
    def pending(self) -> int: ...

    def flush(self) -> str | None: ...


@dataclass(frozen=True)
class CollectorConfig:
    venue: str
    symbols: tuple[str, ...]
    poll_interval_s: int = sources.POLL_INTERVAL_S
    history_refresh_s: int = sources.HISTORY_REFRESH_S
    flush_interval_s: int = sources.FLUSH_INTERVAL_S
    flush_rows: int = sources.FLUSH_ROWS


@dataclass
class Collector:
    config: CollectorConfig
    poller: Poller
    sink: StateSink
    now_ns: Callable[[], int]
    status: Status
    _next_poll_ns: dict[str, int] = field(default_factory=dict)
    _next_history_ns: dict[str, int] = field(default_factory=dict)
    _last_flush_ns: int | None = None

    def step(self) -> None:
        now = self.now_ns()
        if self._last_flush_ns is None:
            self._last_flush_ns = now
        for symbol in self.config.symbols:
            if now >= self._next_history_ns.get(symbol, 0):
                self._load_history(symbol, now)
            if now >= self._next_poll_ns.get(symbol, 0):
                self._poll(symbol, now)
        self._maybe_flush(now)

    # --- what is due ---------------------------------------------------------

    def _load_history(self, symbol: str, now: int) -> None:
        retry = now + self.config.poll_interval_s * SECOND_NS
        try:
            states = self.poller.history(symbol)
        except RateLimited as exc:
            self._failed(exc.endpoint, str(exc))
            self._next_history_ns[symbol] = now + int(exc.retry_after_s * SECOND_NS)
            return
        except PollFailed as exc:
            self._failed(str(exc).split(":")[0], str(exc))
            self._next_history_ns[symbol] = retry
            return
        for state in states:
            self.sink(state)
        self.status.record_success()
        self._next_history_ns[symbol] = now + self.config.history_refresh_s * SECOND_NS

    def _poll(self, symbol: str, now: int) -> None:
        regular = now + self.config.poll_interval_s * SECOND_NS
        try:
            states = self.poller.poll(symbol)
        except RateLimited as exc:
            # Wait what the venue asked, and never less than the cadence.
            self._failed(exc.endpoint, str(exc))
            self._next_poll_ns[symbol] = max(regular, now + int(exc.retry_after_s * SECOND_NS))
            return
        except PollFailed as exc:
            self._failed(str(exc).split(":")[0], str(exc))
            self._next_poll_ns[symbol] = regular
            return
        for state in states:
            self.sink(state)
        self.status.record_success()
        self._next_poll_ns[symbol] = regular

    def _failed(self, endpoint: str, message: str) -> None:
        logger.warning("%s: %s", self.config.venue, message)
        self.status.record_failure(endpoint[:80])

    # --- committing ----------------------------------------------------------

    def _maybe_flush(self, now: int) -> None:
        interval_due = (
            self._last_flush_ns is not None
            and now - self._last_flush_ns >= self.config.flush_interval_s * SECOND_NS
        )
        if interval_due or self.sink.pending >= self.config.flush_rows:
            self._flush(now)

    def _flush(self, now: int) -> None:
        try:
            self.sink.flush()
        except Exception as exc:  # noqa: BLE001 -- a failed commit must not stop the collector
            logger.error("%s: could not commit: %s: %s", self.config.venue, type(exc).__name__, exc)
            self.status.record_flush_failure()
            return
        self._last_flush_ns = now

    def close(self) -> None:
        """Commit what is pending; called on the way out."""
        self._flush(self.now_ns())

    # --- the real loop -------------------------------------------------------

    def run(self, stop: threading.Event, *, tick_s: float = 1.0) -> None:
        try:
            while not stop.is_set():
                self.step()
                stop.wait(tick_s)
        finally:
            self.close()
