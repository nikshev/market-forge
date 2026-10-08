# @trace: REQ-INFRA-007
"""Batching: when a window closes, what a batch is, and that it never changes (FR-006, FR-011)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.batcher import NotWholeSecond, form_batch
from channelflow.notary.scheme import inclusion_proof, merkle_root, verify_inclusion
from tests.notary.conftest import SECOND, record_row, register

WINDOW = 30 * 60 * SECOND
T = 1_791_450_000  # a whole second


def hash_of(row: tables.Row) -> bytes:
    return bytes.fromhex(str(row["record_hash"]))


@pytest.mark.trace("REQ-INFRA-007")
def test_a_window_that_has_not_elapsed_forms_nothing(catalog: Catalog) -> None:
    register(catalog, record_row("a", T, registered_at_ns=T * SECOND))
    batch = form_batch(catalog, now_ns=T * SECOND + WINDOW - 1, window_ns=WINDOW, max_batch=100)
    assert batch is None
    assert tables.batches_table(catalog).read().num_rows == 0


@pytest.mark.trace("REQ-INFRA-007")
def test_an_empty_window_forms_nothing_and_costs_nothing(catalog: Catalog) -> None:
    assert form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100) is None


@pytest.mark.trace("REQ-INFRA-007")
def test_an_elapsed_window_forms_one_batch_over_everything_waiting_in_a_fixed_order(
    catalog: Catalog,
) -> None:
    rows = [
        record_row("b", T + 300, registered_at_ns=T * SECOND),
        record_row("a", T, registered_at_ns=T * SECOND),
        record_row("c", T + 300, kind="decision", registered_at_ns=T * SECOND),
    ]
    register(catalog, *rows)
    batch = form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)

    assert batch is not None
    # Order: bar close, then kind, then id -- "decision" sorts before "snapshot".
    assert [leaf.record_id for leaf in batch.leaves] == ["a", "c", "b"]
    by_id = {r["record_id"]: r for r in rows}
    assert batch.root == merkle_root([hash_of(by_id[i]) for i in ("a", "c", "b")])
    assert batch.bar_ts_s == T + 300  # the largest leaf bar close, in whole seconds
    assert batch.min_bar_close_time_ns == T * SECOND
    assert batch.max_bar_close_time_ns == (T + 300) * SECOND
    # Every leaf has a proof that verifies against the root.
    hashes = [leaf.record_hash for leaf in batch.leaves]
    for leaf in batch.leaves:
        proof = inclusion_proof(hashes, leaf.ordinal)
        assert verify_inclusion(leaf.record_hash, leaf.ordinal, len(hashes), proof, batch.root)


@pytest.mark.trace("REQ-INFRA-007")
def test_a_formed_batch_is_stored_and_its_records_leave_the_waiting_list(catalog: Catalog) -> None:
    register(catalog, record_row("a", T, registered_at_ns=T * SECOND), record_row("b", T + 5))
    batch = form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)

    assert batch is not None
    assert tables.unbatched(tables.records_table(catalog), tables.leaves_table(catalog)) == []
    stored = tables.batches_table(catalog).read().to_pylist()
    assert [r["batch_root"] for r in stored] == [batch.root.hex()]
    assert stored[0]["leaf_count"] == 2
    assert [r["event"] for r in tables.events_table(catalog).read().to_pylist()] == ["formed"]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_batch_is_immutable_and_running_the_batcher_again_re_forms_nothing(
    catalog: Catalog,
) -> None:
    register(catalog, record_row("a", T, registered_at_ns=T * SECOND))
    first = form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)
    again = form_batch(catalog, now_ns=T * SECOND + 2 * WINDOW, window_ns=WINDOW, max_batch=100)

    assert first is not None and again is None
    assert tables.batches_table(catalog).read().num_rows == 1
    assert tables.leaves_table(catalog).read().num_rows == 1


@pytest.mark.trace("REQ-INFRA-007")
def test_a_record_belongs_to_at_most_one_batch_and_later_records_start_the_next(
    catalog: Catalog,
) -> None:
    register(catalog, record_row("a", T, registered_at_ns=T * SECOND))
    first = form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)
    register(catalog, record_row("b", T + 900, registered_at_ns=(T + 900) * SECOND))
    second = form_batch(
        catalog, now_ns=(T + 900) * SECOND + WINDOW, window_ns=WINDOW, max_batch=100
    )

    assert first is not None and second is not None and first.root != second.root
    leaf_ids = [r["record_id"] for r in tables.leaves_table(catalog).read().to_pylist()]
    assert sorted(leaf_ids) == ["a", "b"]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_cap_splits_a_backlog_into_batches_in_order(catalog: Catalog) -> None:
    register(
        catalog,
        *[record_row(f"r{i:02d}", T + i * 10, registered_at_ns=T * SECOND) for i in range(7)],
    )
    batches = []
    while b := form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=3):
        batches.append(b)

    assert [len(b.leaves) for b in batches] == [3, 3, 1]
    flat = [leaf.record_id for b in batches for leaf in b.leaves]
    assert flat == [f"r{i:02d}" for i in range(7)]  # earliest first, never reordered across batches


@pytest.mark.trace("REQ-INFRA-007")
def test_unnotarizable_records_never_enter_a_batch(catalog: Catalog) -> None:
    register(
        catalog,
        record_row("ok", T, registered_at_ns=T * SECOND),
        record_row("bad", T + 5, registered_at_ns=T * SECOND, notarizable="no"),
    )
    batch = form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)

    assert batch is not None and [leaf.record_id for leaf in batch.leaves] == ["ok"]
    assert [r["record_id"] for r in tables.unnotarizable(tables.records_table(catalog))] == ["bad"]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_bar_close_that_is_not_a_whole_second_is_an_error_not_a_rounding(
    catalog: Catalog,
) -> None:
    row = record_row("a", T, registered_at_ns=T * SECOND)
    row["bar_close_time_ns"] = T * SECOND + 1
    register(catalog, row)
    with pytest.raises(NotWholeSecond):
        form_batch(catalog, now_ns=T * SECOND + WINDOW, window_ns=WINDOW, max_batch=100)
    assert tables.batches_table(catalog).read().num_rows == 0  # nothing half-formed
    assert tables.leaves_table(catalog).read().num_rows == 0
