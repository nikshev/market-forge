"""Canonical tables: PRD §29.B's schemas, and the adapters that fill them.

# @trace: REQ-TBL-001

This package is the third place PRD §29.0 asks for -- "any backend-specific DDL
must live behind migrations/adapters and must not leak into signal/channel
domain code". It may import both sides because neither may import the other: the
lakehouse must not know what a `Bar` is, and the bar builder must not know what
Parquet is.

One table so far. The other sixteen §29.B names arrive with the subsystems that
produce them, each with its own requirement.
"""

from channelflow.tables import bars, channels, features, signals
from channelflow.tables.bars import (
    ORDER,
    SCHEMA,
    TABLE_NAME,
    BarSink,
    UnfinalizedBar,
    from_row,
    read_bars,
    table_for,
    to_row,
    write_bars,
)

__all__ = [
    "ORDER",
    "bars",
    "channels",
    "features",
    "signals",
    "SCHEMA",
    "TABLE_NAME",
    "BarSink",
    "UnfinalizedBar",
    "from_row",
    "read_bars",
    "table_for",
    "to_row",
    "write_bars",
]
