"""PRD §29.B's extrema, on the canonical plane.

# @trace: REQ-WP-028

[[REQ-WP-019]]'s detector produces two shapes and neither reached storage: a
candidate while a swing is forming, and a confirmation once the reversal crosses
its threshold.

**The event time of a confirmation is `known_at_ns`, not `extremum_time_ns`.**
That choice is the whole of PRD §45's Phase 1A acceptance -- "no confirmed
extremum can appear earlier than `known_at` in `AS-SEEN-THEN` mode" -- expressed
where the plane can enforce it: a point-in-time read at `t` returns rows whose
event time is at or before `t`, so a turn that had not been confirmed by `t`
cannot come back from a read as of `t`. Keying on the turn's own instant would
have made every point-in-time read a repaint.

The turn's instant is kept beside it, because that is where the marker is drawn
once the row is allowed to be returned at all.

Optional numbers are stored as strings, empty for absent. The plane has no null,
and a float column would have to pick a sentinel -- and a prominence of zero is
a real measurement that would then be indistinguishable from an unmeasured one.
"""

from __future__ import annotations

import uuid

from channelflow.extrema.models import ConfirmedExtremum, ExtremumCandidate, ExtremumType
from channelflow.lakehouse import Column, ObjectStore, Schema, Table
from channelflow.tables.rows import as_decimal, as_float, as_int, as_str

CONFIRMED_TABLE_NAME = "confirmed_extrema"
CANDIDATES_TABLE_NAME = "extremum_candidates"

CONFIRMED_SCHEMA = Schema(
    columns=(
        # When it became knowable. See the module docstring: this being the
        # event time is what makes a point-in-time read honest.
        Column(name="known_at_ns", type="timestamp_ns"),
        Column(name="extremum_id", type="string"),
        Column(name="instrument_id", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="extremum_type", type="string"),
        #: When the turn happened -- where the marker goes.
        Column(name="extremum_time_ns", type="int64"),
        Column(name="price", type="decimal"),
        Column(name="confirmation_method", type="string"),
        Column(name="confirmation_lag_bars", type="int64"),
        Column(name="reversal_bps", type="float64"),
        Column(name="threshold_bps", type="float64"),
        Column(name="prominence_bps", type="string"),
        Column(name="prominence_atr", type="string"),
        Column(name="channel_class", type="string"),
        Column(name="source_candidate_id", type="string"),
    ),
    event_time_column="known_at_ns",
)

#: A candidate's event time is when it was observed, for the same reason.
CANDIDATES_SCHEMA = Schema(
    columns=(
        Column(name="observed_at_ns", type="timestamp_ns"),
        Column(name="candidate_id", type="string"),
        Column(name="instrument_id", type="string"),
        Column(name="venue_scope", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="candidate_type", type="string"),
        Column(name="candidate_time_ns", type="int64"),
        Column(name="price", type="decimal"),
        Column(name="method", type="string"),
        Column(name="structural_score", type="float64"),
        Column(name="channel_position", type="string"),
        Column(name="data_quality", type="string"),
    ),
    event_time_column="observed_at_ns",
)


def confirmed_table_for(store: ObjectStore) -> Table:
    return Table(name=CONFIRMED_TABLE_NAME, schema=CONFIRMED_SCHEMA, store=store)


def candidates_table_for(store: ObjectStore) -> Table:
    return Table(name=CANDIDATES_TABLE_NAME, schema=CANDIDATES_SCHEMA, store=store)


def _optional(value: float | None) -> str:
    """An absent measurement, distinguishably.

    Empty rather than zero: a prominence of zero is a real reading, and a
    sentinel would make an unmeasured turn and a flat one the same row.
    """
    return "" if value is None else repr(value)


def confirmed_row(extremum: ConfirmedExtremum) -> dict[str, object]:
    return {
        "known_at_ns": extremum.known_at_ns,
        "extremum_id": str(extremum.extremum_id),
        "instrument_id": extremum.instrument_id,
        "timeframe_ns": extremum.timeframe_ns,
        "extremum_type": extremum.extremum_type,
        "extremum_time_ns": extremum.extremum_time_ns,
        "price": extremum.price,
        "confirmation_method": extremum.confirmation_method,
        "confirmation_lag_bars": extremum.confirmation_lag_bars,
        "reversal_bps": extremum.reversal_bps,
        "threshold_bps": extremum.threshold_bps,
        "prominence_bps": _optional(extremum.prominence_bps),
        "prominence_atr": _optional(extremum.prominence_atr),
        "channel_class": extremum.channel_class or "",
        "source_candidate_id": (
            "" if extremum.source_candidate_id is None else str(extremum.source_candidate_id)
        ),
    }


def candidate_row(candidate: ExtremumCandidate) -> dict[str, object]:
    return {
        "observed_at_ns": candidate.observed_at_ns,
        "candidate_id": str(candidate.candidate_id),
        "instrument_id": candidate.instrument_id,
        "venue_scope": candidate.venue_scope,
        "timeframe_ns": candidate.timeframe_ns,
        "candidate_type": candidate.candidate_type,
        "candidate_time_ns": candidate.candidate_time_ns,
        "price": candidate.price,
        "method": candidate.method,
        "structural_score": candidate.structural_score,
        "channel_position": _optional(candidate.channel_position),
        "data_quality": candidate.data_quality,
    }


def confirmed_from_row(row: dict[str, object]) -> ConfirmedExtremum:
    source = as_str(row, "source_candidate_id")
    return ConfirmedExtremum(
        extremum_id=uuid.UUID(as_str(row, "extremum_id")),
        instrument_id=as_str(row, "instrument_id"),
        timeframe_ns=as_int(row, "timeframe_ns"),
        extremum_type=_a_type(as_str(row, "extremum_type")),
        extremum_time_ns=as_int(row, "extremum_time_ns"),
        known_at_ns=as_int(row, "known_at_ns"),
        price=as_decimal(row, "price"),
        confirmation_method=as_str(row, "confirmation_method"),
        confirmation_lag_bars=as_int(row, "confirmation_lag_bars"),
        reversal_bps=as_float(row, "reversal_bps"),
        threshold_bps=as_float(row, "threshold_bps"),
        prominence_bps=_read_optional(row, "prominence_bps"),
        prominence_atr=_read_optional(row, "prominence_atr"),
        channel_class=as_str(row, "channel_class") or None,
        source_candidate_id=uuid.UUID(source) if source else None,
    )


def candidate_from_row(row: dict[str, object]) -> ExtremumCandidate:
    return ExtremumCandidate(
        candidate_id=uuid.UUID(as_str(row, "candidate_id")),
        instrument_id=as_str(row, "instrument_id"),
        venue_scope=as_str(row, "venue_scope"),
        timeframe_ns=as_int(row, "timeframe_ns"),
        candidate_type=_a_type(as_str(row, "candidate_type")),
        candidate_time_ns=as_int(row, "candidate_time_ns"),
        observed_at_ns=as_int(row, "observed_at_ns"),
        price=as_decimal(row, "price"),
        method=as_str(row, "method"),
        structural_score=as_float(row, "structural_score"),
        channel_position=_read_optional(row, "channel_position"),
        data_quality=as_str(row, "data_quality"),
    )


def _read_optional(row: dict[str, object], field: str) -> float | None:
    raw = as_str(row, field)
    return None if raw == "" else float(raw)


def _a_type(raw: str) -> ExtremumType:
    if raw not in ("HIGH", "LOW"):
        raise ValueError(f"{raw!r} is not an extremum type; a row that lost it names no turn")
    return raw  # type: ignore[return-value]


def write_confirmed(table: Table, extrema: list[ConfirmedExtremum]) -> None:
    if extrema:
        table.append([confirmed_row(e) for e in extrema])


def write_candidates(table: Table, candidates: list[ExtremumCandidate]) -> None:
    if candidates:
        table.append([candidate_row(c) for c in candidates])


def read_confirmed(
    table: Table,
    *,
    instrument_id: str | None = None,
    timeframe_ns: int | None = None,
    as_of_ns: int | None = None,
) -> list[ConfirmedExtremum]:
    """Confirmed extrema, oldest turn first.

    `as_of_ns` is a **knowledge** filter, not a window: it drops turns that had
    not been confirmed by then. The plane's own point-in-time read does the work,
    because `known_at_ns` is the event time -- see the module docstring.
    """
    rows = (table.read(as_of_ns=as_of_ns) if as_of_ns is not None else table.read()).to_pylist()
    found = [
        confirmed_from_row(row)
        for row in rows
        if (instrument_id is None or row["instrument_id"] == instrument_id)
        and (timeframe_ns is None or row["timeframe_ns"] == timeframe_ns)
    ]
    return sorted(found, key=lambda e: e.extremum_time_ns)


def read_candidates(
    table: Table,
    *,
    instrument_id: str | None = None,
    timeframe_ns: int | None = None,
    as_of_ns: int | None = None,
) -> list[ExtremumCandidate]:
    """Candidates, oldest first, filtered by when they were observed."""
    rows = (table.read(as_of_ns=as_of_ns) if as_of_ns is not None else table.read()).to_pylist()
    found = [
        candidate_from_row(row)
        for row in rows
        if (instrument_id is None or row["instrument_id"] == instrument_id)
        and (timeframe_ns is None or row["timeframe_ns"] == timeframe_ns)
    ]
    return sorted(found, key=lambda c: c.candidate_time_ns)
