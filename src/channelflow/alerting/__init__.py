"""Telegram alerting (REQ-WP-008).

# @trace: REQ-WP-008
# @trace: REQ-US-002
# @trace: REQ-WP-034
# @trace: REQ-WP-035
"""

from channelflow.alerting.dedupe import DedupePolicy
from channelflow.alerting.dispatch import Dispatcher, Notification, Transport
from channelflow.alerting.gate import AlertGate
from channelflow.alerting.models import (
    Alert,
    AttemptOutcome,
    AuditRecord,
    OrderFlowSummary,
    signal_id_for,
)
from channelflow.alerting.outages import OutageAlert, OutageWatch, render_outage
from channelflow.alerting.overlays import Overlay
from channelflow.alerting.render import chart_deep_link, render_message
from channelflow.alerting.stop_updates import (
    StopUpdateAlert,
    StopUpdateGate,
    render_stop_update,
)

__all__ = [
    "Alert",
    "AlertGate",
    "AttemptOutcome",
    "AuditRecord",
    "DedupePolicy",
    "Dispatcher",
    "Notification",
    "OrderFlowSummary",
    "OutageAlert",
    "OutageWatch",
    "Overlay",
    "StopUpdateAlert",
    "StopUpdateGate",
    "Transport",
    "chart_deep_link",
    "render_message",
    "render_outage",
    "render_stop_update",
    "signal_id_for",
]
