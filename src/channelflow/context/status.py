"""The collector's health and metrics, served on a port of its own (REQ-WP-093 FR-013).

# @trace: REQ-WP-093

A collector that has stopped storing is the failure that matters here, because everything
downstream of it degrades into "no data" without saying why. So health is one fact -- *has a poll
succeeded within three intervals* -- and it is both a compose healthcheck (`/healthz`, 200 or 503)
and a metric, with the age of the last success and the failure counts beside it.

A freshly started collector is given the same three intervals before it is called unhealthy:
asking whether something has succeeded before it has had a chance to is not a health check.

The server is the standard library's, in a thread of its own: no new dependency, and the same
shape `channelflow.notary` uses for its own metrics.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SECOND_NS = 1_000_000_000

#: How many poll intervals without a success make the collector unhealthy.
UNHEALTHY_AFTER_INTERVALS = 3


class Status:
    def __init__(self, *, venue: str, poll_interval_s: int, now_ns: Callable[[], int]) -> None:
        self.venue = venue
        self.poll_interval_s = poll_interval_s
        self._now = now_ns
        self._started_ns = now_ns()
        self._last_success_ns: int | None = None
        self.consecutive_failures = 0
        self.failures_total: dict[str, int] = defaultdict(int)
        self.flush_failures = 0
        self._lock = threading.Lock()

    def record_success(self) -> None:
        with self._lock:
            self._last_success_ns = self._now()
            self.consecutive_failures = 0

    def record_failure(self, endpoint: str) -> None:
        with self._lock:
            self.consecutive_failures += 1
            self.failures_total[endpoint] += 1

    def record_flush_failure(self) -> None:
        with self._lock:
            self.flush_failures += 1

    def _reference_ns(self) -> int:
        return self._last_success_ns if self._last_success_ns is not None else self._started_ns

    def healthy(self) -> bool:
        limit = UNHEALTHY_AFTER_INTERVALS * self.poll_interval_s * SECOND_NS
        return self._now() - self._reference_ns() <= limit

    def render_metrics(self) -> str:
        with self._lock:
            now = self._now()
            age = -1 if self._last_success_ns is None else (now - self._last_success_ns) / SECOND_NS
            venue = self.venue
            lines = [
                "# HELP context_last_state_age_seconds Seconds since the last success (-1: none).",
                "# TYPE context_last_state_age_seconds gauge",
                f'context_last_state_age_seconds{{venue="{venue}"}} {age:g}',
                "# HELP context_healthy 1 when a poll has succeeded within three intervals.",
                "# TYPE context_healthy gauge",
                f'context_healthy{{venue="{venue}"}} {1 if self.healthy() else 0}',
                "# HELP context_poll_failures_total Failed requests, by endpoint.",
                "# TYPE context_poll_failures_total counter",
            ]
            for endpoint, count in sorted(self.failures_total.items()):
                lines.append(
                    f'context_poll_failures_total{{venue="{venue}",endpoint="{endpoint}"}} {count}'
                )
            lines += [
                "# HELP context_flush_failures_total Commits that failed and were retried.",
                "# TYPE context_flush_failures_total counter",
                f'context_flush_failures_total{{venue="{venue}"}} {self.flush_failures}',
            ]
        return "\n".join(lines) + "\n"


def serve(
    status: Status, *, port: int, host: str = "0.0.0.0"
) -> tuple[ThreadingHTTPServer, threading.Thread]:  # noqa: S104 -- a container's own port
    """Serve `/healthz` and `/metrics` in a daemon thread; `port=0` picks a free one (tests)."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 -- the standard library's name
            if self.path == "/healthz":
                ok = status.healthy()
                body = b"ok\n" if ok else b"unhealthy\n"
                self.send_response(200 if ok else 503)
            elif self.path == "/metrics":
                body = status.render_metrics().encode()
                self.send_response(200)
            else:
                body = b"not found\n"
                self.send_response(404)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            return  # a health probe every few seconds is not worth a log line each

    server = ThreadingHTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, name="context-status", daemon=True)
    thread.start()
    return server, thread
