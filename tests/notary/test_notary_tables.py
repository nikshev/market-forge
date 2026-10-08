# @trace: REQ-INFRA-007
"""The four notary tables: append-only, with the outbox derived from the event log (FR-008)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import tables as t

ROOT_A, ROOT_B = "aa" * 32, "bb" * 32


def record_row(record_id: str, bar_close: int, *, notarizable: str = "yes") -> dict[str, object]:
    return {
        "bar_close_time_ns": bar_close,
        "record_id": record_id,
        "kind": "snapshot",
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe_ns": 300_000_000_000,
        "record_hash": "11" * 32 if notarizable == "yes" else "",
        "record_bytes": "00",
        "scheme_version": 1,
        "config_hash": "c" * 64,
        "dataset_ref": "d" * 64,
        "dataset_snapshot_id": 7,
        "code_commit": "a" * 40 if notarizable == "yes" else "",
        "notarizable": notarizable,
        "reason": "" if notarizable == "yes" else "commit absent",
        "registered_at_ns": bar_close + 1,
    }


@pytest.mark.trace("REQ-INFRA-007")
def test_registered_ids_and_unbatched_records_follow_the_leaves(catalog: Catalog) -> None:
    records = t.records_table(catalog)
    records.append(
        [record_row("a", 10), record_row("b", 20), record_row("c", 30, notarizable="no")]
    )

    assert t.registered_ids(records) == {"a", "b", "c"}
    assert [r["record_id"] for r in t.unbatched(records, t.leaves_table(catalog))] == ["a", "b"]

    t.leaves_table(catalog).append(
        [
            {
                "bar_close_time_ns": 10,
                "batch_root": ROOT_A,
                "ordinal": 0,
                "record_id": "a",
                "record_hash": "11" * 32,
            }
        ]
    )
    assert [r["record_id"] for r in t.unbatched(records, t.leaves_table(catalog))] == ["b"]
    assert [r["record_id"] for r in t.unnotarizable(records)] == ["c"]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_batchs_state_is_its_latest_event(catalog: Catalog) -> None:
    events = t.events_table(catalog)

    def event(root: str, name: str, at: int, **extra: object) -> dict[str, object]:
        base: dict[str, object] = {
            "event_at_ns": at,
            "batch_root": root,
            "event": name,
            "attempt": 0,
            "tx_hash": "",
            "nonce": -1,
            "block_number": -1,
            "block_time_s": -1,
            "detail": "",
        }
        base.update(extra)
        return base

    events.append(
        [
            event(ROOT_A, "formed", 1),
            event(ROOT_A, "submitted", 2, tx_hash="0x1", attempt=1),
            event(ROOT_A, "confirmed", 3, block_number=9, block_time_s=1_791_000_000),
            event(ROOT_B, "formed", 1),
            event(ROOT_B, "failed", 2, detail="timeout"),
        ]
    )
    state = t.batch_states(events)

    assert state[ROOT_A]["event"] == "confirmed" and state[ROOT_A]["block_number"] == 9
    assert state[ROOT_B]["event"] == "failed" and state[ROOT_B]["detail"] == "timeout"
    assert [r["batch_root"] for r in t.unconfirmed(events)] == [ROOT_B]
