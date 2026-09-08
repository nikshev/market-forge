"""ChannelFlow: crypto market-structure and signal radar.

The product package. Everything under here is subject to `mypy --strict` and to
the constitution in `.specify/memory/constitution.md` -- in particular Principle
I (no look-ahead) and Principle II (event_time, exchange_time, block_time,
ingest_time, bar_open_time and bar_close_time are distinct and never conflated).

Empty by design: REQ-WP-001 provisions the environment, REQ-WP-002 brings the
domain model.
"""

# @trace: REQ-WP-001
# @trace: REQ-WP-002

from decimal import getcontext

# Python's default decimal context rounds every result to 28 significant
# digits. That silently truncated a venue price in REQ-WP-005's VWAP test, and
# the loss turned out to be in `price * quantity` -- affecting the connector's
# notional_quote too, not just the division. REQ-WP-002 claims exact monetary
# arithmetic, so the context is set to match the claim rather than the claim
# narrowed to match the context. See ADR-006.
#
# Division remains inexact in general; 60 digits reduces loss, it does not
# abolish it.
DECIMAL_PRECISION = 60
getcontext().prec = DECIMAL_PRECISION

__all__: list[str] = ["DECIMAL_PRECISION"]
