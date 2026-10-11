"""OKX `liquidation-orders` frames to canonical liquidation events (REQ-WP-094).

# @trace: REQ-WP-094

Pure: a decoded frame in, events out.

**The side is the position's.** In long/short mode OKX names it (`posSide`): a closing `sell` of a
`long` position is a long liquidated. In net mode (`posSide == "net"`) it is the closing order's
side, as on Binance: a `sell` closes a long. A combination that contradicts itself -- a `buy`
closing a `long` -- is stored as `unknown` and not guessed.

**`sz` is contracts**, the same trap `okx.normalize.open_interest_base` documents: BTC-USDT-SWAP
is 0.01 BTC a contract, so reading `sz` as base units overstates a liquidation a hundredfold. The
contract value is passed in by the caller (read from the venue's `instruments`), and an instrument
whose value is not known is *refused*, never guessed. The price is the bankruptcy price (`bkPx`).

The channel carries every SWAP instrument; only those named in `contract_values` -- the ones the
deployment watches -- are returned. A watched instrument whose contract value is `None` (the
instruments answer could not be had) is refused with its name, not guessed and not silently
dropped."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from channelflow.domain import EventMeta, LiquidationEvent

MS_TO_NS = 1_000_000


class LiquidationRefused(ValueError):
    """A detail that is a liquidation and cannot be read as one; the reason is the message."""


def _decimal(detail: dict[str, Any], key: str) -> Decimal:
    try:
        return Decimal(str(detail[key]))
    except (KeyError, InvalidOperation) as exc:
        raise LiquidationRefused(
            f"liquidation-orders: field {key!r} is missing or not a number"
        ) from exc


def _position_side(pos_side: str, side: str) -> str:
    if pos_side == "long":
        return "long_liquidated" if side == "sell" else "unknown"
    if pos_side == "short":
        return "short_liquidated" if side == "buy" else "unknown"
    if pos_side == "net":
        return {"sell": "long_liquidated", "buy": "short_liquidated"}.get(side, "unknown")
    return "unknown"


def liquidation_events(
    frame: dict[str, Any], *, ingest_time_ns: int, contract_values: Mapping[str, Decimal | None]
) -> list[LiquidationEvent]:
    arg = frame.get("arg")
    if not isinstance(arg, dict) or arg.get("channel") != "liquidation-orders":
        return []
    data = frame.get("data")
    if not isinstance(data, list):
        return []  # the subscription acknowledgement carries no data

    events = []
    for item in data:
        symbol = str(item.get("instId", ""))
        if symbol not in contract_values:
            continue
        contract_value = contract_values[symbol]
        if contract_value is None or contract_value <= 0:
            raise LiquidationRefused(
                f"liquidation-orders: {symbol} has no usable contract value ({contract_value}); "
                "its size in base units cannot be derived"
            )
        for detail in item.get("details") or []:
            price = _decimal(detail, "bkPx")
            contracts = _decimal(detail, "sz")
            if price <= 0 or contracts <= 0:
                raise LiquidationRefused(
                    f"liquidation-orders: price {price} and size {contracts} must be positive"
                )
            try:
                event_time_ns = int(detail["ts"]) * MS_TO_NS
            except (KeyError, TypeError, ValueError) as exc:
                raise LiquidationRefused("liquidation-orders: no usable time `ts`") from exc
            qty = contracts * contract_value
            events.append(
                LiquidationEvent(
                    meta=EventMeta(
                        source="okx-ws-liquidation",
                        venue="okx",
                        market_type="perp",
                        symbol=symbol,
                        event_time_ns=event_time_ns,
                        ingest_time_ns=ingest_time_ns,
                        sequence=None,
                        source_event_id=None,
                    ),
                    side=_position_side(str(detail.get("posSide")), str(detail.get("side"))),  # type: ignore[arg-type]
                    price=price,
                    qty=qty,
                    notional_usd=price * qty,
                )
            )
    return events
