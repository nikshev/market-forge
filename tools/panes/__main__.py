# @trace: REQ-WP-097
"""`python -m tools.panes`: the state of every lower pane of every market, from the live API.

    python -m tools.panes --api http://127.0.0.1:8000

Exit 0: every cell is `data` or `absent` with a reason the system gave.
Exit 1: some cell is `no-producer` -- empty, and nothing says why.
Exit 2: the API could not be reached.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence

from tools.panes.classify import (
    NO_PRODUCER,
    Evidence,
    PaneState,
    classify,
    count_features,
)
from tools.panes.fetch import ApiUnreachable, Get, http_get, panes_from_page

HOUR_NS = 3_600_000_000_000


def gather(
    get: Get, *, venue: str, symbol: str, timeframe_ns: int, start_ns: int, end_ns: int
) -> Evidence:
    params = {
        "venue": venue,
        "symbol": symbol,
        "timeframe_ns": str(timeframe_ns),
        "start_ns": str(start_ns),
        "end_ns": str(end_ns),
    }
    status, series = get("/api/v1/features/timeseries", params)
    counts = count_features(series.get("points", [])) if status == 200 and series else {}
    status, bars = get("/api/v1/bars", params)
    bar_count = len(bars.get("bars", [])) if status == 200 and bars else 0

    reasons: list[str] | None = None
    error: str | None = None
    status, consensus = get(
        "/api/v1/consensus",
        {
            "venue": venue,
            "symbol": symbol,
            "timeframe_ns": str(timeframe_ns),
            "window": "24h",
        },
    )
    if status == 200 and consensus:
        rows = consensus.get("consensus", [])
        reasons = [r["refusal_reason"] for r in rows if r.get("refusal_reason")]
        if not reasons and rows:
            reasons = []
    else:
        error = f"HTTP {status}" + (
            f" {consensus.get('detail')}" if isinstance(consensus, dict) else ""
        )
    return Evidence(counts, bar_count, reasons, error)


def run(
    get: Get,
    *,
    panes: Sequence[tuple[str, str]],
    hours: int,
    now_ns: int,
    only_timeframes: Sequence[str] | None = None,
) -> tuple[list[str], bool]:
    """The report's lines, and whether any cell is `no-producer`."""
    status, listed = get("/api/v1/markets", {})
    if status != 200 or not listed:
        raise ApiUnreachable(f"/api/v1/markets answered HTTP {status}")
    status, offered = get("/api/v1/timeframes", {})
    if status != 200 or not offered:
        raise ApiUnreachable(f"/api/v1/timeframes answered HTTP {status}")
    timeframes = [
        t for t in offered["timeframes"] if only_timeframes is None or t["token"] in only_timeframes
    ]

    lines: list[str] = []
    failed = False
    for market in listed["markets"]:
        for timeframe in timeframes:
            evidence = gather(
                get,
                venue=market["venue"],
                symbol=market["symbol"],
                timeframe_ns=timeframe["timeframe_ns"],
                start_ns=now_ns - hours * HOUR_NS,
                end_ns=now_ns,
            )
            heading = f"{market['venue']} {market['symbol']} ({market['market_type']})"
            lines.append(f"{heading} {timeframe['token']}")
            for feature, label in panes:
                state: PaneState = classify(feature, evidence)
                failed = failed or state.state == NO_PRODUCER
                lines.append(f"    {label:<24} {state.render()}")
    return lines, failed


def main(argv: list[str] | None = None, *, get: Get | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--hours", type=int, default=24, help="how far back to look")
    parser.add_argument(
        "--timeframes", default="1m,15m,1h", help="comma list of timeframe tokens, or 'all'"
    )
    args = parser.parse_args(argv)
    chosen = None if args.timeframes == "all" else [t.strip() for t in args.timeframes.split(",")]
    try:
        lines, failed = run(
            get or http_get(args.api),
            panes=panes_from_page(),
            hours=args.hours,
            now_ns=time.time_ns(),
            only_timeframes=chosen,
        )
    except ApiUnreachable as exc:
        print(f"the API could not be read: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    print(
        "\nNO PRODUCER: at least one pane is empty and nothing says why."
        if failed
        else "\nevery pane has data or a stated reason."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
