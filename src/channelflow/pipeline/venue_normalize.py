"""Venue-aware normalizer dispatcher for ingest daemon.

# @trace: REQ-WP-076

This module provides a unified interface for normalizing trade frames from
different venues (Binance, Bybit, OKX) into canonical TradeEvents.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from channelflow.connectors.binance import normalize as binance_normalize
from channelflow.connectors.binance.normalize import NormalizationError as BinanceNormalizationError
from channelflow.connectors.bybit.normalize import NormalizationError as BybitNormalizationError
from channelflow.connectors.bybit.normalize import public_trade as bybit_public_trade
from channelflow.connectors.okx.normalize import NormalizationError as OkxNormalizationError
from channelflow.connectors.okx.normalize import public_trade as okx_public_trade


class NormalizationError(ValueError):
    """A frame that could not be normalized for any venue."""

    pass


class FrameParseError(NormalizationError):
    """JSON parse error."""

    pass


class InvalidEnvelopeError(NormalizationError):
    """Invalid envelope structure."""

    pass


class NotATradeStreamError(NormalizationError):
    """Frame is not a trade stream (ignored, not an error)."""

    pass


def _normalize_binance(
    envelope: dict[str, Any], market_type: str, ingest_time_ns: int
) -> list[Any]:
    """Normalize a Binance trade frame."""
    stream = envelope.get("stream")
    payload = envelope.get("data")
    if not isinstance(stream, str) or not isinstance(payload, dict):
        raise InvalidEnvelopeError("invalid Binance envelope")
    if not stream.endswith("@aggTrade"):
        raise NotATradeStreamError("not a trade stream")

    trade = binance_normalize.agg_trade(
        payload,
        venue="binance",
        market_type=market_type,
        ingest_time_ns=ingest_time_ns,
    )
    return [trade]


def _normalize_bybit(envelope: dict[str, Any], market_type: str, ingest_time_ns: int) -> list[Any]:
    """Normalize a Bybit trade frame."""
    topic = envelope.get("topic", "")
    if not topic.startswith("publicTrade."):
        raise NotATradeStreamError("not a publicTrade topic")

    data = envelope.get("data")
    if not isinstance(data, list):
        raise BybitNormalizationError("data is not a list")

    trades = []
    for trade_data in data:
        trade = bybit_public_trade(
            trade_data,
            venue="bybit",
            market_type=market_type,
            ingest_time_ns=ingest_time_ns,
        )
        trades.append(trade)
    return trades


def _normalize_okx(envelope: dict[str, Any], market_type: str, ingest_time_ns: int) -> list[Any]:
    """Normalize an OKX trade frame."""
    data = envelope.get("data")
    if not isinstance(data, list):
        raise OkxNormalizationError("data is not a list")

    trades = []
    for trade_data in data:
        # Contract value for OKX instruments - hardcoded defaults for known instruments
        # TODO: Replace with proper instruments registry
        inst_id = trade_data.get("instId", "")
        contract_value = Decimal("0.01") if inst_id == "BTC-USDT-SWAP" else Decimal("1")

        trade = okx_public_trade(
            trade_data,
            venue="okx",
            market_type=market_type,
            contract_value=contract_value,
            ingest_time_ns=ingest_time_ns,
        )
        trades.append(trade)
    return trades


def normalize_frame(
    venue: str,
    market_type: str,
    frame: str,
    ingest_time_ns: int,
) -> tuple[list[Any], str | None]:
    """
    Normalize a single frame into a list of TradeEvents.

    Args:
        venue: The venue name ("binance", "bybit", "okx")
        market_type: The market type ("spot", "swap", etc.)
        frame: The raw frame as a JSON string
        ingest_time_ns: The ingestion timestamp in nanoseconds

    Returns:
        Tuple of (trades_list, error_category) where error_category is:
        - None: success
        - "parse": JSON parse error
        - "envelope": Invalid envelope structure
        - "not_trade": Not a trade stream (ignored)
        - "normalization": Normalization error (unparsed)

    Raises:
        NormalizationError: If the frame cannot be normalized for an unknown venue
    """
    try:
        envelope = json.loads(frame)
    except ValueError:
        return [], "parse"

    if venue == "binance":
        try:
            return _normalize_binance(envelope, market_type, ingest_time_ns), None
        except NotATradeStreamError:
            return [], "not_trade"
        except (BinanceNormalizationError, InvalidEnvelopeError):
            return [], "normalization"
    elif venue == "bybit":
        try:
            return _normalize_bybit(envelope, market_type, ingest_time_ns), None
        except NotATradeStreamError:
            return [], "not_trade"
        except (BybitNormalizationError, OkxNormalizationError):
            return [], "normalization"
    elif venue == "okx":
        try:
            return _normalize_okx(envelope, market_type, ingest_time_ns), None
        except NotATradeStreamError:
            return [], "not_trade"
        except OkxNormalizationError:
            return [], "normalization"
    else:
        raise NormalizationError(f"unknown venue: {venue}")


def normalize_frames(
    venue: str,
    market_type: str,
    frames: list[str],
    ingest_time_ns: int,
) -> tuple[list[Any], int, int, int]:
    """
    Normalize a list of frames into TradeEvents.

    Returns:
        Tuple of (trades_list, unparsed_count, ignored_count, parse_error_count)
    """
    all_trades = []
    unparsed = 0
    ignored = 0
    parse_errors = 0
    for frame in frames:
        trades, error = normalize_frame(venue, market_type, frame, ingest_time_ns)
        if error == "parse":
            parse_errors += 1
        elif error == "envelope":
            parse_errors += 1
        elif error == "not_trade":
            ignored += 1
        elif error == "normalization":
            unparsed += 1
        else:
            all_trades.extend(trades)
    return all_trades, unparsed, ignored, parse_errors
