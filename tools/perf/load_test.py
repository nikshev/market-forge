"""Drive concurrent traffic at a running deployment and report §36's targets.

# @trace: REQ-WP-067

Run deliberately, against a stack that is up -- the same rule the capture tools
follow, and for the same reason [[REQ-WP-057]] gives: a duration measured on a
shared CI runner is a fact about the runner.

    .venv/bin/python -m tools.perf.load_test --base-url http://127.0.0.1:8000

**Two of §36's three targets cannot be measured from outside.** `feature update`
and `signal after bar close` are pipeline timings, not HTTP ones, and this tool
reports them as `not measured` rather than leaving them out -- which is the
whole reason that verdict exists.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence

from channelflow.perf.load import LoadResult, drive, passed, report

#: §36's "chart historical load p95 < 2s for 2,000 bars". The request the chart
#: itself makes, at the size the target names.
BARS = "/api/v1/bars"
BARS_LIMIT = 2000

DEFAULT_CONCURRENCIES = (1, 4, 16)
DEFAULT_REQUESTS = 64


def fetch(url: str, *, timeout: float) -> None:
    """One request. Raises on anything that is not a 200, so it counts as an
    error rather than as a fast success."""
    with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
        if response.status != 200:
            raise urllib.error.HTTPError(url, response.status, "not 200", response.headers, None)
        response.read()


def run(
    *,
    base_url: str,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    concurrencies: Sequence[int],
    requests: int,
    timeout: float,
) -> list[LoadResult]:
    query = urllib.parse.urlencode(
        {"venue": venue, "symbol": symbol, "timeframe_ns": timeframe_ns, "limit": BARS_LIMIT}
    )
    url = f"{base_url.rstrip('/')}{BARS}?{query}"

    # One warm-up, outside the measurement: the first request pays for a
    # connection and a cold catalog read, and whether it is slow is a different
    # question from what a loaded system costs.
    fetch(url, timeout=timeout)

    results = []
    for concurrency in concurrencies:
        results.append(
            drive(
                lambda: fetch(url, timeout=timeout),
                name="chart_historical_load",
                concurrency=concurrency,
                requests=max(requests, concurrency),
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--venue", default="binance")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe-ns", type=int, default=60_000_000_000)
    parser.add_argument("--requests", type=int, default=DEFAULT_REQUESTS)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--concurrency", type=int, action="append", default=None, dest="concurrencies"
    )
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args(argv)

    results = run(
        base_url=arguments.base_url,
        venue=arguments.venue,
        symbol=arguments.symbol,
        timeframe_ns=arguments.timeframe_ns,
        concurrencies=arguments.concurrencies or list(DEFAULT_CONCURRENCIES),
        requests=arguments.requests,
        timeout=arguments.timeout,
    )

    print("measured shape:")
    for result in results:
        print(
            f"  concurrency {result.concurrency:>3}: "
            f"p50 {result.measurement.p50_ns / 1e6:8.2f}ms  "
            f"p95 {result.measurement.p95_ns / 1e6:8.2f}ms  "
            f"spread {result.measurement.spread:5.2f}x  "
            f"errors {result.errors}"
        )

    reports = report(results)
    print("\n§36's targets:")
    for item in reports:
        print(f"  {item.line}")

    if arguments.json:
        print(
            json.dumps(
                [
                    {
                        "target": item.target.name,
                        "verdict": str(item.verdict),
                        "concurrency": item.concurrency,
                        "p95_ns": item.p95_ns,
                        "errors": item.errors,
                    }
                    for item in reports
                ],
                indent=2,
            )
        )

    return 0 if passed(reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
