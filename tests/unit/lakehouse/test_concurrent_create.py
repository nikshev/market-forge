"""Two writers appending to a table that does not exist yet (REQ-WP-081).

Found by the market-registration tests, not by any lakehouse test. `IcebergTable.append` looked for
the
table, found none, and created it -- three steps that are not one. Five ingest daemons restarted
together
after a deploy do exactly that to a fresh `markets` table, and four of them lost:
`TableAlreadyExistsError`,
which registration (rightly) treats as a warning and moves on, leaving four markets unlisted. The
single-process tests could not see it because nothing else was creating the table at the time.
"""

from __future__ import annotations

import threading

import pytest

from channelflow.lakehouse import Catalog, IcebergTable

from .conftest import trade, trades_schema

WRITERS = 5


@pytest.mark.trace("REQ-WP-081")
def test_writers_racing_to_create_the_same_table_all_land(catalog: Catalog) -> None:
    errors: list[BaseException] = []
    barrier = threading.Barrier(WRITERS)

    def write(index: int) -> None:
        handle = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
        try:
            barrier.wait(timeout=30)  # as close to simultaneous as threads get
            handle.append([trade(index)])
        except BaseException as error:  # noqa: BLE001 -- any failure fails the assertion below
            errors.append(error)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(1, WRITERS + 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert errors == [], [repr(e) for e in errors]
    reader = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
    assert reader.read().num_rows == WRITERS, "every writer's row landed exactly once"


@pytest.mark.trace("REQ-WP-081")
def test_the_writer_that_lost_the_race_returns_its_own_snapshot(catalog: Catalog) -> None:
    """The loser must not just survive: what it gets back describes what it wrote."""
    winner = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
    loser = IcebergTable(name="cex_trades", schema=trades_schema(), catalog=catalog)
    # Make the loser look first (the table is absent), then let the winner create it, then let the
    # loser create: the exact interleaving of the race, with no threads and no luck.
    loser._table = _lying_once(loser, catalog)  # type: ignore[method-assign]
    winner.append([trade(1)])

    described = loser.append([trade(2)])

    assert described.record_count == 2
    assert loser.read().num_rows == 2


def _lying_once(table: IcebergTable, catalog: Catalog):  # type: ignore[no-untyped-def]
    """`_table` that says 'no such table' on the first call and tells the truth afterwards."""
    real = table.__class__._table.__get__(table)
    state = {"first": True}

    def lookup():  # type: ignore[no-untyped-def]
        if state["first"]:
            state["first"] = False
            return None
        return real()

    return lookup
