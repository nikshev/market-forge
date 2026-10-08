"""What is notarized, in its canonical encoding (REQ-INFRA-007).

# @trace: REQ-INFRA-007

Three kinds. A **snapshot** is the existing `channel_snapshots` row, encoded by the existing
schema -- no second definition of what a snapshot *is* (FR-002). A **decision** has no table to
reuse, so its row is declared here in the lakehouse's own vocabulary and encoded by the same
`Schema.encode_row`. A **suppression** is the freshness gate's recorded refusal.

A decision is one transition of a candidate's history. The one that matters most is the silence:
a candidate that reaches a terminal state without ever having been `ALERTED` is a NO ALERT,
carrying the reason of the transition that ended it. PRD §2 promises "NO ALERT, with a reason";
nothing persisted one before this.

Nothing that is not final is registered. The model forbids a snapshot that saw the future at
construction; this module checks again, because the notary must not depend on a guard it does
not own (Principle I).
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.alerting import signal_id_for
from channelflow.alerting.models import AuditRecord
from channelflow.channels import ChannelSnapshot
from channelflow.lakehouse import Column, Schema
from channelflow.signals import Candidate, CandidateState
from channelflow.signals.models import TERMINAL
from channelflow.tables import channels as channels_table


class NotFinal(ValueError):
    """A record that is not final, or that saw the future, was offered. It is refused."""


@dataclass(frozen=True)
class Record:
    kind: str  # snapshot | decision | suppression
    record_id: str
    #: `bar_close_time` of the bar that made the record final -- what latency is measured from.
    bar_close_time_ns: int
    venue: str
    symbol: str
    timeframe_ns: int
    data: bytes  # the canonical bytes


DECISION_SCHEMA = Schema(
    columns=(
        Column(name="bar_close_time_ns", type="timestamp_ns"),
        Column(name="signal_id", type="string"),
        Column(name="ordinal", type="int64"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="direction", type="string"),
        Column(name="boundary", type="string"),
        Column(name="from_state", type="string"),
        Column(name="to_state", type="string"),
        Column(name="reason", type="string"),
        Column(name="verdict", type="string"),
        Column(name="alerted_before", type="string"),
    ),
    event_time_column="bar_close_time_ns",
)

SUPPRESSION_SCHEMA = Schema(
    columns=(
        Column(name="bar_close_time_ns", type="timestamp_ns"),
        Column(name="signal_id", type="string"),
        Column(name="symbol", type="string"),
        #: When the gate was offered the alert -- its own time, never the bar's.
        Column(name="queued_at_ns", type="int64"),
        Column(name="status", type="string"),
        Column(name="reason", type="string"),
    ),
    event_time_column="bar_close_time_ns",
)

ALERT = "ALERT"
NO_ALERT = "NO_ALERT"
STEP = "STEP"


def snapshot_record(
    snapshot: ChannelSnapshot,
    *,
    venue: str,
    symbol: str,
    timeframe_ns: int,
    bar_final: bool = True,
) -> Record:
    if not bar_final:
        raise NotFinal(f"{venue} {symbol} snapshot at {snapshot.as_of_ns}: its bar is not final")
    if snapshot.source_max_event_time_ns > snapshot.as_of_ns:
        raise NotFinal(
            f"{venue} {symbol} snapshot at {snapshot.as_of_ns}: source_max_event_time_ns "
            f"{snapshot.source_max_event_time_ns} is after as_of_ns (PRD section 13.1)"
        )
    row = channels_table.to_row(snapshot, venue=venue, symbol=symbol, timeframe_ns=timeframe_ns)
    return Record(
        kind="snapshot",
        record_id=f"snapshot|{venue}|{symbol}|{timeframe_ns}|{snapshot.as_of_ns}",
        bar_close_time_ns=snapshot.as_of_ns,
        venue=venue,
        symbol=symbol,
        timeframe_ns=timeframe_ns,
        data=channels_table.SCHEMA.encode_row(row),
    )


def decision_records(candidate: Candidate) -> list[Record]:
    """One record per transition of the candidate's history, in order.

    A longer history extends the list and never renumbers it: transition *i* keeps its identity
    and its bytes however many transitions follow, which is what lets a candidate seen early and
    seen again later register only what is new.
    """
    signal_id = str(signal_id_for(candidate))
    records: list[Record] = []
    alerted = False
    for ordinal, transition in enumerate(candidate.history):
        if transition.to_state == CandidateState.ALERTED:
            verdict = ALERT
        elif transition.to_state in TERMINAL and not alerted:
            verdict = NO_ALERT
        else:
            verdict = STEP
        row: dict[str, object] = {
            "bar_close_time_ns": transition.bar_close_time_ns,
            "signal_id": signal_id,
            "ordinal": ordinal,
            "venue": candidate.venue,
            "symbol": candidate.symbol,
            "timeframe_ns": candidate.timeframe_ns,
            "direction": candidate.direction,
            "boundary": candidate.boundary,
            "from_state": transition.from_state.value,
            "to_state": transition.to_state.value,
            "reason": transition.reason,
            "verdict": verdict,
            "alerted_before": "yes" if alerted else "no",
        }
        records.append(
            Record(
                kind="decision",
                record_id=f"decision|{signal_id}|{ordinal}",
                bar_close_time_ns=transition.bar_close_time_ns,
                venue=candidate.venue,
                symbol=candidate.symbol,
                timeframe_ns=candidate.timeframe_ns,
                data=DECISION_SCHEMA.encode_row(row),
            )
        )
        if transition.to_state == CandidateState.ALERTED:
            alerted = True
    return records


def suppression_record(audit: AuditRecord, *, bar_close_time_ns: int) -> Record:
    """The gate's refusal to send, as a decision. The caller supplies the bar it concerned."""
    if audit.status != "suppressed":
        raise ValueError(f"only a suppressed alert is a suppression, not {audit.status!r}")
    row: dict[str, object] = {
        "bar_close_time_ns": bar_close_time_ns,
        "signal_id": str(audit.signal_id),
        "symbol": audit.symbol,
        "queued_at_ns": audit.queued_at_ns,
        "status": audit.status,
        "reason": audit.reason,
    }
    return Record(
        kind="suppression",
        record_id=f"suppression|{audit.signal_id}|{audit.queued_at_ns}",
        bar_close_time_ns=bar_close_time_ns,
        venue="",
        symbol=audit.symbol,
        timeframe_ns=0,
        data=SUPPRESSION_SCHEMA.encode_row(row),
    )
