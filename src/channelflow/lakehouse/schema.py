"""A table's columns, and the fingerprint that identifies them.

# @trace: REQ-STORE-001

The type vocabulary is closed and small on purpose. PRD section 29.B lists
seventeen canonical tables whose columns are prices, sizes, identifiers, flags
and event times; a wider vocabulary would mean more ways for two writers to
disagree about what a column is, and the fingerprint exists precisely so they
cannot.

The fingerprint covers the column names, their types and their order. Order is
part of the identity because it is part of the physical layout: a table whose
columns were reordered is a different table to read, and calling it the same one
would let a reader line up the wrong values with the right names.
"""

from __future__ import annotations

import hashlib
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import pyarrow as pa

#: What a column may hold. Each maps to exactly one Arrow type, and each has
#: exactly one canonical byte encoding for hashing.
ColumnType = Literal[
    "int64",
    "float64",
    "string",
    "bool",
    "timestamp_ns",
    "decimal",
    # Containers. PRD section 29.6 asks a channel snapshot for "forecast arrays"
    # and "quality components" by name, so a table that could only hold scalars
    # would need a child table per tuple -- six of them across section 29.B's
    # schemas, each joined back on every read. Arrow and Parquet carry all three
    # natively and DuckDB and Trino query them, which is the whole reason the
    # physical format was chosen.
    "float_list",
    "string_list",
    "float_map",
]

_ARROW: dict[str, pa.DataType] = {
    "int64": pa.int64(),
    "float64": pa.float64(),
    "string": pa.string(),
    "bool": pa.bool_(),
    # Event times are nanoseconds since the epoch, stored as int64 rather than
    # as an Arrow timestamp: every timestamp in this repository is an integer
    # nanosecond count, and converting at the storage boundary would introduce a
    # unit and a timezone that nothing upstream has.
    "timestamp_ns": pa.int64(),
    # Stored as its exact string form, not as a float or an Arrow decimal.
    # A price is money: float64 cannot hold 0.1, and an Arrow decimal needs a
    # precision and scale declared per column, which PRD section 29's schemas do
    # not give and which would silently truncate the first value that exceeded
    # them. A string round-trips every `Decimal` exactly and costs bytes.
    "decimal": pa.string(),
    "float_list": pa.list_(pa.float64()),
    "string_list": pa.list_(pa.string()),
    "float_map": pa.map_(pa.string(), pa.float64()),
}

#: One byte per type, so two values of different types can never hash alike.
_TAG: dict[str, bytes] = {
    "int64": b"i",
    "float64": b"f",
    "string": b"s",
    "bool": b"b",
    "timestamp_ns": b"t",
    "decimal": b"d",
    "float_list": b"L",
    "string_list": b"S",
    "float_map": b"M",
}


class UnknownColumn(KeyError):
    """A row or a filter named a column the schema does not have."""


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a column needs a name")
        if self.type not in _ARROW:
            raise ValueError(
                f"{self.type!r} is not one of the storage types ({', '.join(sorted(_ARROW))})"
            )


@dataclass(frozen=True)
class Schema:
    """The columns of a table, and which of them carries event time."""

    columns: tuple[Column, ...]
    #: The column a point-in-time read filters on. `None` for a table that has
    #: no event time -- a configuration table, say -- and such a table refuses a
    #: point-in-time read rather than answering one it cannot answer.
    event_time_column: str | None = None

    def __post_init__(self) -> None:
        if not self.columns:
            raise ValueError("a schema needs at least one column")
        names = [column.name for column in self.columns]
        if len(set(names)) != len(names):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValueError(f"duplicate column(s): {', '.join(duplicates)}")
        if self.event_time_column is not None:
            column = self.column(self.event_time_column)
            if column.type != "timestamp_ns":
                raise ValueError(
                    f"{column.name!r} is the event-time column and is typed "
                    f"{column.type!r}; a point-in-time filter compares nanosecond "
                    "counts and cannot compare anything else"
                )

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(column.name for column in self.columns)

    def column(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise UnknownColumn(f"{name!r} is not a column of this schema ({', '.join(self.names)})")

    @property
    def fingerprint(self) -> str:
        """A stable identity for these columns, in this order, with these types.

        Stable across processes and across library versions: it is computed from
        the schema's own declaration and never from anything Arrow or Parquet
        writes into a file.
        """
        digest = hashlib.sha256()
        for column in self.columns:
            digest.update(_length_prefixed(column.name.encode()))
            digest.update(_length_prefixed(column.type.encode()))
        digest.update(_length_prefixed((self.event_time_column or "").encode()))
        return digest.hexdigest()

    @property
    def map_columns(self) -> tuple[str, ...]:
        """Columns Arrow hands back as a list of pairs rather than as a mapping.

        Named for the same reason as `decimal_columns`: a reader that forgot one
        would get `[("fit", 0.9)]` where it expected `{"fit": 0.9}`, and the
        mistake surfaces wherever the value is finally used rather than where it
        was read.
        """
        return tuple(c.name for c in self.columns if c.type == "float_map")

    @property
    def decimal_columns(self) -> tuple[str, ...]:
        """Columns stored as text that a reader has to turn back into `Decimal`.

        Named here rather than rediscovered by each reader: a caller that forgot
        one would compare a string against a number and find nothing, which
        reads as an empty result rather than as a mistake.
        """
        return tuple(c.name for c in self.columns if c.type == "decimal")

    def arrow(self) -> pa.Schema:
        return pa.schema([pa.field(c.name, _ARROW[c.type]) for c in self.columns])

    def encode_row(self, row: dict[str, object]) -> bytes:
        """One row's canonical bytes, in column order.

        Length-prefixed per value, so no separator can be forged by a value that
        happens to contain one. This encoding -- not the Parquet file -- is what
        a content hash is taken over.
        """
        unknown = sorted(set(row) - set(self.names))
        if unknown:
            raise UnknownColumn(
                f"row carries {', '.join(unknown)}, which the schema does not "
                f"declare ({', '.join(self.names)})"
            )
        parts: list[bytes] = []
        for column in self.columns:
            if column.name not in row:
                raise UnknownColumn(
                    f"row is missing {column.name!r}; a missing value written as a "
                    "default would say 'none' where it means 'unknown', and the "
                    "content hash would agree with both"
                )
            parts.append(_TAG[column.type])
            parts.append(_length_prefixed(_encode(column.type, row[column.name])))
        return b"".join(parts)


def _length_prefixed(payload: bytes) -> bytes:
    return struct.pack("<I", len(payload)) + payload


def _encode(column_type: str, value: object) -> bytes:
    """One value's canonical bytes.

    Floats are hashed as their IEEE-754 bytes rather than as text. That makes
    `-0.0` and `0.0` hash differently even though they compare equal, which is
    the conservative reading for a dataset identity: they are distinct bit
    patterns, Parquet stores them distinctly, and a hash that called them the
    same would let a file change without its identity changing.
    """
    if column_type in ("int64", "timestamp_ns"):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"expected an int for a {column_type} column, got {value!r}")
        return struct.pack("<q", value)
    if column_type == "float64":
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise TypeError(f"expected a float for a float64 column, got {value!r}")
        return struct.pack("<d", float(value))
    if column_type == "bool":
        if not isinstance(value, bool):
            raise TypeError(f"expected a bool for a bool column, got {value!r}")
        return b"\x01" if value else b"\x00"
    if column_type == "float_list":
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TypeError(f"expected a sequence for a float_list column, got {value!r}")
        return b"".join(_length_prefixed(_encode("float64", item)) for item in value)
    if column_type == "string_list":
        if isinstance(value, str) or not isinstance(value, Sequence):
            raise TypeError(f"expected a sequence for a string_list column, got {value!r}")
        return b"".join(_length_prefixed(_encode("string", item)) for item in value)
    if column_type == "float_map":
        if not isinstance(value, Mapping):
            raise TypeError(f"expected a mapping for a float_map column, got {value!r}")
        # Keys sorted: a map is not ordered, and two writers that inserted the
        # same pairs in different orders wrote the same value.
        return b"".join(
            _length_prefixed(_encode("string", key))
            + _length_prefixed(_encode("float64", value[key]))
            for key in sorted(value)
        )
    if column_type == "decimal":
        if not isinstance(value, Decimal):
            raise TypeError(f"expected a Decimal for a decimal column, got {value!r}")
        # The exact string form, so `Decimal("1.10")` and `Decimal("1.1")` are
        # different content. They compare equal and carry different exponents,
        # Parquet stores the two strings distinctly, and a hash calling them the
        # same would let a stored value change without its identity changing --
        # the same reading `-0.0` gets above.
        return str(value).encode()
    if not isinstance(value, str):
        raise TypeError(f"expected a str for a string column, got {value!r}")
    return value.encode("utf-8")
