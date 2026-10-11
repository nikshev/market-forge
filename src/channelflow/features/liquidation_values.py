"""The liquidation features as of a bar's close, from stored events and heartbeats (REQ-WP-094).

# @trace: REQ-WP-094

Pure, like `context_values`: no table, no clock, nothing that reaches a storage backend.

**Quiet is a reading only where the stream was listening.** Zero liquidated in five minutes is
true of a market the stream watched for all five and a lie about one it did not, so a window is
evaluated only if every minute of it has a heartbeat (`covered`); otherwise *no* liquidation
feature exists for that close. And the imbalance of a covered window with nothing in it is absent,
not zero -- the library's `LiquidationWindow.imbalance` already says so: zero would read "both
sides equally", which is a fact about a busy window.

**What was knowable at the close.** An event counts if its event time is at or before the close
*and* the stream had delivered it by then; one dated before the close that arrived after it, or
one a fast venue clock dated after the close, is not in the bar.

`liquidation_intensity_5m` and `time_since_liquidation_spike` are not written: no pane reads them,
intensity needs the trailing five minutes' traded volume which a bar of another timeframe does not
carry, and a spike needs a per-symbol threshold nobody has chosen. They stay registered, with
their library functions, and are not produced -- a stated absence, not a silent one."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence

from channelflow.derivatives.liquidations import window
from channelflow.domain import LiquidationEvent

MINUTE_NS = 60_000_000_000
WINDOW_NS = 5 * MINUTE_NS

LIQUIDATION_FEATURES: tuple[str, ...] = (
    "liquidation_long_usd_5m",
    "liquidation_short_usd_5m",
    "liquidation_imbalance_5m",
)


def covered(heartbeats: Sequence[int], *, close_ns: int, window_ns: int = WINDOW_NS) -> bool:
    """Whether every minute of `(close - window, close]` has a heartbeat.

    A heartbeat is dated at the end of the minute it covers, so the five minutes of a five-minute
    window are the slots `(close - 5m, close - 4m]` ... `(close - 1m, close]`, and each needs at
    least
    one. Two heartbeats in one minute do not stand in for two minutes. `heartbeats` is sorted
    ascending, as `tables.liquidations.read` returns it: a sort here would be paid per bar.
    """
    ordered = heartbeats
    for slot in range(window_ns // MINUTE_NS):
        end = close_ns - slot * MINUTE_NS
        start = end - MINUTE_NS
        i = bisect_right(ordered, start)
        if i >= len(ordered) or ordered[i] > end:
            return False
    return True


def liquidation_values(
    events: Sequence[LiquidationEvent],
    heartbeats: Sequence[int],
    *,
    close_ns: int,
    **_: object,
) -> dict[str, float]:
    """The three liquidation features at `close_ns`, or nothing where the window was not covered."""
    if not covered(heartbeats, close_ns=close_ns):
        return {}
    received = [
        e for e in events if e.meta.event_time_ns <= close_ns and e.meta.ingest_time_ns <= close_ns
    ]
    inside = window(received, as_of_ns=close_ns, window_ns=WINDOW_NS)
    values = {
        "liquidation_long_usd_5m": float(inside.long_usd),
        "liquidation_short_usd_5m": float(inside.short_usd),
    }
    if inside.imbalance is not None:
        values["liquidation_imbalance_5m"] = inside.imbalance
    return values
