"""Rows are narrowed in Arrow before they become Python objects (REQ-WP-104).

`table.read().to_pylist()` turns every row of a table into a dict of Python objects before anything
is asked of it. On 2026-10-13 the features table held over a million rows and a request for one
series' last day converted all of them: five seconds, to keep a few thousand. The filter belongs on
the columns; the dicts are for what is left.
"""

from __future__ import annotations

import pyarrow as pa
import pytest

from channelflow.tables.rows import narrow

pytestmark = pytest.mark.trace("REQ-WP-104")


def table() -> pa.Table:
    return pa.table(
        {
            "venue": ["a", "a", "b", "b", "a"],
            "symbol": ["X", "Y", "X", "Y", "X"],
            "at": [1, 2, 3, 4, 5],
        }
    )


def test_it_keeps_only_the_rows_equal_in_every_named_column() -> None:
    got = narrow(table(), venue="a", symbol="X")

    assert got.to_pydict() == {"venue": ["a", "a"], "symbol": ["X", "X"], "at": [1, 5]}


def test_it_keeps_the_order_the_rows_had() -> None:
    assert narrow(table(), venue="a")["at"].to_pylist() == [1, 2, 5]


def test_naming_nothing_keeps_everything() -> None:
    assert narrow(table()).num_rows == 5


def test_a_value_nothing_holds_leaves_no_rows_and_keeps_the_columns() -> None:
    got = narrow(table(), venue="zzz")

    assert got.num_rows == 0
    assert got.column_names == ["venue", "symbol", "at"]


def test_a_range_keeps_both_ends() -> None:
    got = narrow(table(), at=(2, 4))

    assert got["at"].to_pylist() == [2, 3, 4]


def test_a_range_may_be_open_at_either_end() -> None:
    assert narrow(table(), at=(4, None))["at"].to_pylist() == [4, 5]
    assert narrow(table(), at=(None, 2))["at"].to_pylist() == [1, 2]


def test_equal_and_range_together() -> None:
    assert narrow(table(), venue="a", at=(2, 5))["at"].to_pylist() == [2, 5]


def test_an_empty_table_is_narrowed_to_an_empty_table() -> None:
    empty = table().slice(0, 0)

    assert narrow(empty, venue="a").num_rows == 0


def test_a_column_the_table_does_not_have_is_an_error_not_an_empty_answer() -> None:
    with pytest.raises(KeyError):
        narrow(table(), nope="x")


def test_none_means_do_not_filter_on_this_column() -> None:
    """Callers pass optional filters straight through: `None` is "not asked", never "is null"."""
    assert narrow(table(), venue=None, symbol="X").num_rows == 3
