"""Binance connector exports.

# @trace: REQ-WP-003
# @trace: REQ-WP-076
"""

from channelflow.connectors.binance.connector import BinanceConnector
from channelflow.connectors.binance.instruments import instruments_from
from channelflow.connectors.binance.normalize import (
    NormalizationError,
    agg_trade,
    depth_snapshot,
    depth_update,
    trade,
)

__all__ = [
    "BinanceConnector",
    "NormalizationError",
    "agg_trade",
    "trade",
    "depth_update",
    "depth_snapshot",
    "instruments_from",
]