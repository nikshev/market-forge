"""Reading one value out of a stored row, or refusing.

# @trace: REQ-STORE-002
# @trace: REQ-WP-104

A row that comes back from the plane is `dict[str, object]`: Arrow knows the
column's type and Python's type checker does not. Every table module needs the
same handful of coercions, and writing them inline in five modules would mean
five places where a silent `float(...)` could creep into a column that holds
money.

These refuse rather than coerce across kinds. `int("12")` and `float("1.0")`
both succeed on a string, and a column that returned a string where a number was
expected is a schema drift worth a traceback rather than a plausible number.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

import pyarrow as pa
import pyarrow.compute as pc


class RowShape(TypeError):
    """A stored column held something its schema says it cannot."""


def as_int(row: Mapping[str, object], field: str) -> int:
    value = row[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise RowShape(f"{field!r} is {value!r}; the column holds integers")
    return value


def as_float(row: Mapping[str, object], field: str) -> float:
    value = row[field]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise RowShape(f"{field!r} is {value!r}; the column holds numbers")
    return float(value)


def as_str(row: Mapping[str, object], field: str) -> str:
    value = row[field]
    if not isinstance(value, str):
        raise RowShape(f"{field!r} is {value!r}; the column holds text")
    return value


def as_bool(row: Mapping[str, object], field: str) -> bool:
    value = row[field]
    if not isinstance(value, bool):
        raise RowShape(f"{field!r} is {value!r}; the column holds booleans")
    return value


def as_decimal(row: Mapping[str, object], field: str) -> Decimal:
    """A decimal column, stored as its exact text.

    `Decimal(str(...))` on anything else would accept a float and reintroduce
    the rounding the column type exists to prevent -- so the stored value has to
    already be the text it was written as.
    """
    value = row[field]
    if not isinstance(value, str):
        raise RowShape(
            f"{field!r} is {value!r}; a decimal column holds the value's exact text, "
            "and anything else has already lost precision"
        )
    return Decimal(value)


def as_float_tuple(row: Mapping[str, object], field: str) -> tuple[float, ...]:
    value = row[field]
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise RowShape(f"{field!r} is {value!r}; the column holds a list of numbers")
    return tuple(float(item) for item in value)


def as_str_tuple(row: Mapping[str, object], field: str) -> tuple[str, ...]:
    value = row[field]
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise RowShape(f"{field!r} is {value!r}; the column holds a list of text")
    return tuple(str(item) for item in value)


def as_float_map(row: Mapping[str, object], field: str) -> dict[str, float]:
    """A map column, which Arrow hands back as a list of pairs.

    A mapping is accepted too, so a caller that has already converted one does
    not have to know which shape it holds.
    """
    value = row[field]
    if isinstance(value, Mapping):
        return {str(k): float(v) for k, v in value.items()}
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise RowShape(f"{field!r} is {value!r}; the column holds a map of numbers")
    return {str(key): float(item) for key, item in value}


def narrow(rows: pa.Table, /, **conditions: object | tuple[int | None, int | None]) -> pa.Table:
    """The rows of `rows` that meet every condition, still an Arrow table ([[REQ-WP-104]]).

    A value keeps the rows whose column equals it; a `(low, high)` pair keeps those between, both
    ends included, either open with `None`; `None` for a whole condition means "not asked" and
    filters nothing, so a caller's optional arguments pass straight through. Order is kept.

    This exists so the filter runs on the columns, before `to_pylist()` makes a Python dict of
    every row: a read of one series out of a table of a million rows used to build a million dicts
    to keep a few thousand. An unknown column raises `KeyError` -- an empty answer would be a typo
    reading as a quiet market.
    """
    mask = None
    for name, wanted in conditions.items():
        column = rows[name]
        if wanted is None:
            continue
        if isinstance(wanted, tuple):
            low, high = wanted
            parts = []
            if low is not None:
                parts.append(pc.greater_equal(column, low))
            if high is not None:
                parts.append(pc.less_equal(column, high))
            if not parts:
                continue
            condition = parts[0] if len(parts) == 1 else pc.and_(parts[0], parts[1])
        else:
            condition = pc.equal(column, wanted)
        mask = condition if mask is None else pc.and_(mask, condition)
    return rows if mask is None else rows.filter(mask)
