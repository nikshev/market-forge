# @trace: REQ-INFRA-007
"""What is notarized: final snapshots, and decisions including NO ALERT (FR-002, FR-004, FR-005)."""

from __future__ import annotations

import struct
import uuid

import pytest

from channelflow.alerting import signal_id_for
from channelflow.alerting.models import AuditRecord
from channelflow.channels import ChannelQuality, ChannelSnapshot
from channelflow.lakehouse import Schema
from channelflow.notary.records import (
    DECISION_SCHEMA,
    SUPPRESSION_SCHEMA,
    NotFinal,
    Record,
    decision_records,
    snapshot_record,
    suppression_record,
)
from channelflow.signals import Candidate, CandidateState, Transition
from channelflow.tables import channels as channels_table

MINUTE_NS = 60 * 1_000_000_000
AS_OF = 1_788_838_800_000_000_000


def make_snapshot(**overrides: object) -> ChannelSnapshot:
    fields: dict[str, object] = {
        "as_of_ns": AS_OF,
        "model_name": "rolling_ols",
        "model_version": "1.0.0",
        "lookback": 60,
        "center_now": 100.0,
        "upper_now": 105.0,
        "lower_now": 95.0,
        "slope_normalized": 0.5,
        "width_pct": 10.0,
        "quality": ChannelQuality(score=0.8, submetrics={}, contributing=(), unavailable=()),
        "source_max_event_time_ns": AS_OF - MINUTE_NS,
    }
    fields.update(overrides)
    return ChannelSnapshot(**fields)  # type: ignore[arg-type]


def candidate(*steps: tuple[str, str, int, str], **overrides: object) -> Candidate:
    """A candidate whose history is the given (from, to, bar_close_ns, reason) steps."""
    history = tuple(
        Transition(
            from_state=CandidateState(a), to_state=CandidateState(b), bar_close_time_ns=t, reason=r
        )
        for a, b, t, r in steps
    )
    fields: dict[str, object] = {
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe_ns": 5 * MINUTE_NS,
        "direction": "short",
        "boundary": "upper",
        "state": history[-1].to_state,
        "opened_at_ns": history[0].bar_close_time_ns,
        "bars_since_open": len(history),
        "history": history,
    }
    fields.update(overrides)
    return Candidate(**fields)  # type: ignore[arg-type]


T0 = AS_OF
EXPIRED_STEPS = (
    ("none", "approach", T0, "price entered the upper zone"),
    ("approach", "touch", T0 + 5 * MINUTE_NS, "price touched the boundary"),
    ("touch", "expired", T0 + 50 * MINUTE_NS, "no rejection within 10 bars"),
)
EXPIRED_NEVER_ALERTED = candidate(*EXPIRED_STEPS)
ALERTED_THEN_INVALIDATED = candidate(
    ("none", "approach", T0, "entered"),
    ("approach", "touch", T0 + 5 * MINUTE_NS, "touched"),
    ("touch", "rejection_pending", T0 + 10 * MINUTE_NS, "closed back inside"),
    ("rejection_pending", "confirmed", T0 + 15 * MINUTE_NS, "held"),
    ("confirmed", "alerted", T0 + 15 * MINUTE_NS, "sent"),
    ("alerted", "invalidated", T0 + 40 * MINUTE_NS, "closed beyond the invalidation"),
)


@pytest.mark.trace("REQ-INFRA-007")
def test_a_snapshots_canonical_bytes_are_the_lakehouses_own_row_encoding() -> None:
    snapshot = make_snapshot()
    record = snapshot_record(
        snapshot, venue="binance", symbol="BTCUSDT", timeframe_ns=5 * MINUTE_NS
    )

    row = channels_table.to_row(
        snapshot, venue="binance", symbol="BTCUSDT", timeframe_ns=5 * MINUTE_NS
    )
    assert record.data == channels_table.SCHEMA.encode_row(row)
    assert record.kind == "snapshot"
    assert record.bar_close_time_ns == AS_OF
    assert record.record_id == f"snapshot|binance|BTCUSDT|{5 * MINUTE_NS}|{AS_OF}"


@pytest.mark.trace("REQ-INFRA-007")
def test_a_snapshot_whose_bar_is_not_final_is_refused() -> None:
    with pytest.raises(NotFinal, match="not final"):
        snapshot_record(
            make_snapshot(),
            venue="binance",
            symbol="BTCUSDT",
            timeframe_ns=5 * MINUTE_NS,
            bar_final=False,
        )


@pytest.mark.trace("REQ-INFRA-007")
def test_a_snapshot_that_saw_the_future_is_refused_even_if_built_around_the_model() -> None:
    """Principle I. The model forbids it at construction; the notary does not rely on that alone."""
    leaking = make_snapshot()
    object.__setattr__(leaking, "source_max_event_time_ns", AS_OF + 1)  # around the validator
    with pytest.raises(NotFinal, match="source_max_event_time"):
        snapshot_record(leaking, venue="binance", symbol="BTCUSDT", timeframe_ns=5 * MINUTE_NS)


@pytest.mark.trace("REQ-INFRA-007")
def test_expiring_without_ever_alerting_is_a_no_alert_decision_carrying_its_reason() -> None:
    records = decision_records(EXPIRED_NEVER_ALERTED)

    assert [r.kind for r in records] == ["decision"] * 3
    last = records[-1]
    values = _decode(DECISION_SCHEMA, last)
    assert values["verdict"] == "NO_ALERT"
    assert values["reason"] == "no rejection within 10 bars"
    assert values["to_state"] == "expired" and values["alerted_before"] == "no"
    assert last.bar_close_time_ns == T0 + 50 * MINUTE_NS
    # The earlier steps are decisions too, but not silences.
    assert [_decode(DECISION_SCHEMA, r)["verdict"] for r in records[:-1]] == ["STEP", "STEP"]


@pytest.mark.trace("REQ-INFRA-007")
def test_reaching_alerted_is_an_alert_and_a_later_invalidation_is_not_a_no_alert() -> None:
    records = decision_records(ALERTED_THEN_INVALIDATED)
    rows = [_decode(DECISION_SCHEMA, r) for r in records]

    assert [r["verdict"] for r in rows] == ["STEP", "STEP", "STEP", "STEP", "ALERT", "STEP"]
    assert rows[-1]["to_state"] == "invalidated" and rows[-1]["alerted_before"] == "yes"


@pytest.mark.trace("REQ-INFRA-007")
def test_a_decision_is_identified_by_its_signal_and_its_position_in_the_history() -> None:
    records = decision_records(EXPIRED_NEVER_ALERTED)
    signal_id = signal_id_for(EXPIRED_NEVER_ALERTED)

    assert [r.record_id for r in records] == [f"decision|{signal_id}|{i}" for i in range(3)]
    assert [_decode(DECISION_SCHEMA, r)["ordinal"] for r in records] == [0, 1, 2]
    again = decision_records(EXPIRED_NEVER_ALERTED)
    assert [r.record_id for r in again] == [r.record_id for r in records]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_longer_history_extends_the_same_decisions_and_never_renumbers_them() -> None:
    """A candidate seen early and again later: the early decisions keep their identity and bytes."""
    early = candidate(*EXPIRED_STEPS[:2])
    early_records = decision_records(early)
    later_records = decision_records(EXPIRED_NEVER_ALERTED)

    assert [r.record_id for r in early_records] == [r.record_id for r in later_records[:2]]
    assert [r.data for r in early_records] == [r.data for r in later_records[:2]]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_suppression_is_a_decision_with_the_reason_the_gate_recorded() -> None:
    audit = AuditRecord(
        signal_id=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        symbol="BTCUSDT",
        queued_at_ns=T0 + 1,
        status="suppressed",
        reason="book is stale by 9000000000ns, over the 5000000000ns tolerance",
    )
    record = suppression_record(audit, bar_close_time_ns=T0)

    assert record.kind == "suppression"
    assert record.record_id == f"suppression|{audit.signal_id}|{T0 + 1}"
    assert record.bar_close_time_ns == T0
    row = _decode(SUPPRESSION_SCHEMA, record)
    assert str(row["reason"]).startswith("book is stale") and row["status"] == "suppressed"


@pytest.mark.trace("REQ-INFRA-007")
def test_only_a_suppressed_audit_record_is_a_suppression() -> None:
    delivered = AuditRecord(
        signal_id=uuid.uuid4(), symbol="BTCUSDT", queued_at_ns=1, status="delivered", reason="ok"
    )
    with pytest.raises(ValueError, match="suppressed"):
        suppression_record(delivered, bar_close_time_ns=T0)


def _decode(schema: Schema, record: Record) -> dict[str, object]:
    """Read a canonical row back: the inverse of `Schema.encode_row` for the column types used."""
    data, at, out = record.data, 0, {}
    for column in schema.columns:
        at += 1  # the type tag
        (length,) = struct.unpack_from("<I", data, at)
        at += 4
        payload = data[at : at + length]
        at += length
        if column.type == "string":
            out[column.name] = payload.decode()
        elif column.type in ("int64", "timestamp_ns"):
            out[column.name] = struct.unpack("<q", payload)[0]
        else:  # pragma: no cover - not used by these schemas
            raise AssertionError(column.type)
    return out
