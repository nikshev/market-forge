"""Backtest v1 (REQ-WP-010).

# @trace: REQ-WP-010
# @trace: REQ-US-005
# @trace: REQ-BT-001
"""

from channelflow.backtest.economics import (
    CostModel,
    CostsRequired,
    EconomicReport,
    NothingResolved,
    economic_report,
)
from channelflow.backtest.families import (
    FAMILIES,
    MIDDLE_CONTINUATION_SHORT,
    UPPER_REJECTION_SHORT,
    SetupFamily,
)
from channelflow.backtest.fills import (
    Fill,
    NoFillAvailable,
    market_at_next_open,
    market_at_signal_close,
)
from channelflow.backtest.outcomes import (
    HorizonUnavailable,
    Outcome,
    SignalOutcome,
    resolve_outcome,
)
from channelflow.backtest.report import FORBIDDEN_ECONOMIC_FIELDS, BacktestReport
from channelflow.backtest.runner import BacktestRunner

__all__ = [
    "FAMILIES",
    "CostModel",
    "CostsRequired",
    "EconomicReport",
    "Fill",
    "HorizonUnavailable",
    "NoFillAvailable",
    "NothingResolved",
    "Outcome",
    "SignalOutcome",
    "economic_report",
    "market_at_next_open",
    "market_at_signal_close",
    "resolve_outcome",
    "FORBIDDEN_ECONOMIC_FIELDS",
    "MIDDLE_CONTINUATION_SHORT",
    "UPPER_REJECTION_SHORT",
    "BacktestReport",
    "BacktestRunner",
    "SetupFamily",
]
