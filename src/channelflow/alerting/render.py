"""PRD section 26.1's message and section 27.1's deep link.

# @trace: REQ-WP-008

Section 26.1 gives ten blocks. Four have no source today -- score (section 43's
ranker), model probability (Principle IV forbids a model before baselines),
derivatives (REQ-WP-013) and DeFi (REQ-WP-014/015). ADR-016: those blocks are
*absent*, not rendered with dashes.

That is not tidiness. A reader scanning a dozen alerts on a phone reads the
shape before the numbers, and `Score: -` sitting where `Score: 82/100` sits in
every other message is a formatting difference, not an absence.

No clock: every timestamp comes from the alert's own event time.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import quote

from channelflow.alerting.models import Alert

#: PRD section 26.1's header marks. Direction, not severity -- ADR-016 leaves
#: severity to section 43's ranker.
DIRECTION_MARK = {"short": "🔴", "long": "🟢"}

SETUP_NAMES = {
    ("short", "upper"): "Upper Channel Rejection",
    ("long", "lower"): "Lower Channel Rejection",
    ("short", "middle"): "Mid-Channel Rejection Short",
    ("long", "middle"): "Mid-Channel Rejection Long",
}


def render_message(alert: Alert) -> str:
    """The message, as a reader sees it."""
    candidate = alert.candidate
    lines = [
        f"{DIRECTION_MARK[candidate.direction]} {candidate.symbol} "
        f"— {candidate.direction.upper()} SETUP",
        "",
        f"Venue: {candidate.venue}",
        f"TF: {_timeframe(candidate.timeframe_ns)}",
        f"Price: {_thousands(alert.price)}",
        f"Time: {_utc_minute(alert.event_time_ns)}",
        "",
        f"Setup: {SETUP_NAMES[(candidate.direction, candidate.boundary)]}",
    ]

    if alert.channel is not None:
        channel = alert.channel
        span = channel.upper_now - channel.lower_now
        position = (float(alert.price) - channel.lower_now) / span if span else 0.5
        lines += [
            "",
            "Channel",
            f"Direction: {'DOWN' if channel.slope_normalized < 0 else 'UP'}",
            f"Slope: {channel.slope_normalized * 100:.2f}% / lookback",
            f"Width: {channel.width_pct * 100:.1f}%",
            f"Position: {position:.2f}",
            f"Quality: {channel.quality.score:.2f}",
        ]

    if alert.order_flow is not None:
        flow = alert.order_flow
        lines += [
            "",
            "Order Flow",
            f"OFI 30s: {flow.ofi_30s}",
            f"Depth imbalance 25bps: {flow.depth_imbalance_25bps:.2f}",
            f"{'Ask' if candidate.direction == 'short' else 'Bid'}-wall persistence: "
            f"{flow.wall_persistence}",
        ]

    lines += [
        "",
        f"Invalidation: {_thousands(alert.invalidation_price)}",
        f"Research target: {_thousands(alert.research_target_price)}",
    ]
    return "\n".join(lines)


def chart_deep_link(alert: Alert) -> str:
    """PRD section 27.1's link, plus section 27.2's active layers.

    `/chart/:venue/:symbol?tf=..&at=..&signal=<uuid>[&overlays=..]`

    The host is the alert's own, never a constant here -- a hard-coded one
    works in exactly one deployment.
    """
    candidate = alert.candidate
    at = _utc_iso(alert.event_time_ns)
    link = (
        f"{alert.chart_base_url.rstrip('/')}"
        f"/chart/{quote(candidate.venue)}/{quote(candidate.symbol)}"
        f"?tf={_timeframe(candidate.timeframe_ns)}"
        f"&at={quote(at, safe='')}"
        f"&signal={alert.signal_id}"
    )
    if not alert.overlays:
        # Omitted, never defaulted. A default written here would claim the alert
        # knew what was on screen, and the chart would restore a state nobody
        # recorded (REQ-US-002, FR-002).
        return link
    # Sorted and deduplicated, so one alert is one link. Serialized in whatever
    # order the tuple held, a resent alert would carry a different URL and look
    # like a different signal.
    names = ",".join(sorted({o.value for o in alert.overlays}))
    return f"{link}&overlays={quote(names, safe='')}"


def _timeframe(timeframe_ns: int) -> str:
    minutes = timeframe_ns // (60 * 1_000_000_000)
    if minutes % (60 * 24) == 0:
        return f"{minutes // (60 * 24)}d"
    if minutes % 60 == 0:
        return f"{minutes // 60}h"
    return f"{minutes}m"


def _thousands(value: Decimal) -> str:
    return f"{value:,.0f}"


def _utc_minute(event_time_ns: int) -> str:
    return _moment(event_time_ns).strftime("%Y-%m-%d %H:%M UTC")


def _utc_iso(event_time_ns: int) -> str:
    return _moment(event_time_ns).strftime("%Y-%m-%dT%H:%M:%SZ")


def _moment(event_time_ns: int) -> datetime:
    """Event time to a UTC moment.

    Integer division before constructing the datetime: going through a float
    loses nanosecond precision, and a timestamp that drifts by a microsecond
    between two renders would break determinism for no visible reason.
    """
    return datetime.fromtimestamp(event_time_ns // 1_000_000_000, tz=UTC)
