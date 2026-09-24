"""Binance connector exports.

# @trace: REQ-WP-076
"""

from channelflow.connectors.binance.connector import BinanceConnector
from channelflow.connectors.binance.normalize import (
    NormalizationError,
    agg_trade,
    trade,
    depth_update,
    depth_snapshot,
)
from channelflow.connectors.binance.instruments import instruments_from

__all__ = [
    "BinanceConnector",
    "NormalizationError",
    "agg_trade",
    "trade",
    "depth_update",
    "depth_snapshot",
    "instruments_from",
]