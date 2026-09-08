"""Telegram alerting (REQ-WP-008).

# @trace: REQ-WP-008
"""

from channelflow.alerting.dedupe import DedupePolicy
from channelflow.alerting.dispatch import Dispatcher, Transport
from channelflow.alerting.gate import AlertGate
from channelflow.alerting.models import (
    Alert,
    AttemptOutcome,
    AuditRecord,
    OrderFlowSummary,
    signal_id_for,
)
from channelflow.alerting.render import chart_deep_link, render_message

__all__ = [
    "Alert",
    "AlertGate",
    "AttemptOutcome",
    "AuditRecord",
    "DedupePolicy",
    "Dispatcher",
    "OrderFlowSummary",
    "Transport",
    "chart_deep_link",
    "render_message",
    "signal_id_for",
]
