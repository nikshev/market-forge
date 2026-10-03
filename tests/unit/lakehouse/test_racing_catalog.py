"""The race helpers do what they say (REQ-WP-079).

A green test behind a wrapper that does nothing proves nothing, so the wrappers are tested before
anything is tested through them.
"""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog, IcebergTable

from .conftest import trade, trades_schema
from .racing import CountingCatalog, RacingCatalog


def _table(catalog: Catalog | CountingCatalog | RacingCatalog) -> IcebergTable:
    return IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-WP-079")
def test_the_counter_counts_exactly_the_loads_a_call_makes(catalog: Catalog) -> None:
    _table(catalog).append([trade(1)])
    counting = CountingCatalog(catalog)
    table = _table(counting)

    assert counting.total == 0
    table.snapshot_ids()
    assert counting.total == 1
    counting.reset()
    assert counting.total == 0


@pytest.mark.trace("REQ-WP-079")
def test_under_the_racing_catalog_each_load_after_the_first_holds_one_more_snapshot(
    catalog: Catalog,
) -> None:
    writer = _table(catalog)
    writer.append([trade(1)])
    counter = iter(range(2, 1000))
    racing = RacingCatalog(catalog, lambda: writer.append([trade(next(counter))]))
    reader = _table(racing)

    racing.arm()
    first = reader.snapshot_ids()
    second = reader.snapshot_ids()
    third = reader.snapshot_ids()

    assert len(first) == 1, "the first load after arming is the clean one"
    assert len(second) == len(first) + 1
    assert len(third) == len(second) + 1
    assert racing.competing_commits == 2


@pytest.mark.trace("REQ-WP-079")
def test_a_racing_catalog_does_nothing_until_it_is_armed(catalog: Catalog) -> None:
    writer = _table(catalog)
    writer.append([trade(1)])
    racing = RacingCatalog(catalog, lambda: writer.append([trade(99)]))
    reader = _table(racing)

    reader.snapshot_ids()
    reader.snapshot_ids()

    assert racing.competing_commits == 0
    assert len(reader.snapshot_ids()) == 1


@pytest.mark.trace("REQ-WP-079")
def test_the_competing_commit_goes_through_the_inner_catalog_and_is_not_counted(
    catalog: Catalog,
) -> None:
    writer = _table(catalog)
    writer.append([trade(1)])
    counting = CountingCatalog(catalog)
    racing = RacingCatalog(counting, lambda: writer.append([trade(2)]))
    reader = _table(racing)

    racing.arm()
    reader.snapshot_ids()
    reader.snapshot_ids()

    assert counting.total == 2, "two reads, two loads; the competitor's own loads are not in it"
