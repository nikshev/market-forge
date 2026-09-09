"""Backtest v1 (REQ-WP-010).

# @trace: REQ-WP-010
# @trace: REQ-US-005
"""

from channelflow.backtest.families import (
    FAMILIES,
    MIDDLE_CONTINUATION_SHORT,
    UPPER_REJECTION_SHORT,
    SetupFamily,
)
from channelflow.backtest.report import FORBIDDEN_ECONOMIC_FIELDS, BacktestReport
from channelflow.backtest.runner import BacktestRunner

__all__ = [
    "FAMILIES",
    "FORBIDDEN_ECONOMIC_FIELDS",
    "MIDDLE_CONTINUATION_SHORT",
    "UPPER_REJECTION_SHORT",
    "BacktestReport",
    "BacktestRunner",
    "SetupFamily",
]
