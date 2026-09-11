"""PRD §29.7's `signals`, and the transitions that led to each.

# @trace: REQ-STORE-002

    ## 29.7. `signals`
    Immutable decision core plus separate resolution/outcome table.
    Never update original feature values after signal.

Two tables, because §29.7 asks for two: a decision core that is written once,
and a separate table for what happened afterwards. A candidate's `history` is
neither of those — it is the record of how the decision was reached — so it goes
in its own child table rather than into either.

The alternative was four parallel lists on the parent row (`from_state[]`,
`to_state[]`, `bar_close_time_ns[]`, `reason[]`). The plane can hold those, and
they would be four columns that only mean anything read together, in an order
nothing enforces. A child table with one row per transition is queryable in
DuckDB by itself, which is what a transition history is usually asked about.
"""

from __future__ import annotations

import uuid

from channelflow.alerting import signal_id_for
from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema
from channelflow.signals import Candidate, CandidateState, Transition
from channelflow.tables.rows import as_int, as_str

TABLE_NAME = "signals"
TRANSITIONS_TABLE_NAME = "signal_transitions"

#: The decision core. `signal_id` is the same identity the alert's deep link
#: uses -- [[REQ-WP-008]]'s `signal_id_for` -- so a stored signal and a link to it
#: name the same thing, and a different id here would make every link a 404 while
#: looking entirely correct.
SCHEMA = Schema(
    columns=(
        Column(name="opened_at_ns", type="timestamp_ns"),
        Column(name="signal_id", type="string"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="direction", type="string"),
        Column(name="boundary", type="string"),
        Column(name="state", type="string"),
        Column(name="bars_since_open", type="int64"),
    ),
    event_time_column="opened_at_ns",
)

#: One row per transition, keyed back to its signal. `bar_close_time_ns` is the
#: event time: a transition is knowable when the bar that caused it closes.
TRANSITIONS_SCHEMA = Schema(
    columns=(
        Column(name="bar_close_time_ns", type="timestamp_ns"),
        Column(name="signal_id", type="string"),
        Column(name="ordinal", type="int64"),
        Column(name="from_state", type="string"),
        Column(name="to_state", type="string"),
        Column(name="reason", type="string"),
    ),
    event_time_column="bar_close_time_ns",
)

ORDER = ("venue", "symbol", "timeframe_ns", "opened_at_ns")


def to_rows(candidate: Candidate) -> tuple[dict[str, object], list[dict[str, object]]]:
    """One candidate as its core row and its transition rows.

    The `ordinal` on each transition is its position in the history. Two
    transitions can share a bar close time -- a touch and a rejection inside one
    bar -- and without an ordinal the order of a history would depend on how the
    rows came back, which is not an order at all.
    """
    signal_id = str(signal_id_for(candidate))
    core: dict[str, object] = {
        "opened_at_ns": candidate.opened_at_ns,
        "signal_id": signal_id,
        "venue": candidate.venue,
        "symbol": candidate.symbol,
        "timeframe_ns": candidate.timeframe_ns,
        "direction": candidate.direction,
        "boundary": candidate.boundary,
        "state": str(candidate.state),
        "bars_since_open": candidate.bars_since_open,
    }
    transitions = [
        {
            "bar_close_time_ns": transition.bar_close_time_ns,
            "signal_id": signal_id,
            "ordinal": index,
            "from_state": str(transition.from_state),
            "to_state": str(transition.to_state),
            "reason": transition.reason,
        }
        for index, transition in enumerate(candidate.history)
    ]
    return core, transitions


def from_rows(core: dict[str, object], transitions: list[dict[str, object]]) -> Candidate:
    """A candidate back from its two tables, history in its recorded order."""
    ordered = sorted(transitions, key=lambda row: as_int(row, "ordinal"))
    return Candidate(
        venue=as_str(core, "venue"),
        symbol=as_str(core, "symbol"),
        timeframe_ns=as_int(core, "timeframe_ns"),
        direction=as_str(core, "direction"),  # type: ignore[arg-type]
        boundary=as_str(core, "boundary"),  # type: ignore[arg-type]
        state=CandidateState(as_str(core, "state")),
        opened_at_ns=as_int(core, "opened_at_ns"),
        bars_since_open=as_int(core, "bars_since_open"),
        history=tuple(
            Transition(
                from_state=CandidateState(as_str(row, "from_state")),
                to_state=CandidateState(as_str(row, "to_state")),
                bar_close_time_ns=as_int(row, "bar_close_time_ns"),
                reason=as_str(row, "reason"),
            )
            for row in ordered
        ),
    )


def table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TABLE_NAME, schema=SCHEMA, catalog=catalog)


def transitions_table_for(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=TRANSITIONS_TABLE_NAME, schema=TRANSITIONS_SCHEMA, catalog=catalog)


def write_signals(
    core_table: IcebergTable, transitions_table: IcebergTable, candidates: list[Candidate]
) -> None:
    """Write candidates and their transitions.

    Two commits, and they are not atomic together: the plane's atomicity is per
    table. The core is written **last**, so a failure between them leaves
    transitions nothing points at -- unreferenced rows a reader joining from the
    core will never see -- rather than a signal whose history is missing, which
    would read as a signal that came from nowhere.
    """
    if not candidates:
        return
    cores: list[dict[str, object]] = []
    all_transitions: list[dict[str, object]] = []
    for candidate in candidates:
        core, transitions = to_rows(candidate)
        cores.append(core)
        all_transitions.extend(transitions)
    if all_transitions:
        transitions_table.append(all_transitions)
    core_table.append(cores)


def read_signals(
    core_table: IcebergTable,
    transitions_table: IcebergTable,
    *,
    symbol: str | None = None,
    timeframe_ns: int | None = None,
    state: str | None = None,
    start_ns: int | None = None,
    end_ns: int | None = None,
) -> list[Candidate]:
    """Signals matching the filters, oldest first, each with its history."""
    cores = [
        row
        for row in core_table.read().to_pylist()
        if (symbol is None or row["symbol"] == symbol)
        and (timeframe_ns is None or row["timeframe_ns"] == timeframe_ns)
        and (state is None or row["state"] == state)
        and (start_ns is None or as_int(row, "opened_at_ns") >= start_ns)
        and (end_ns is None or as_int(row, "opened_at_ns") <= end_ns)
    ]
    if not cores:
        return []
    by_signal: dict[str, list[dict[str, object]]] = {}
    for row in transitions_table.read().to_pylist():
        by_signal.setdefault(as_str(row, "signal_id"), []).append(row)
    cores.sort(key=lambda row: as_int(row, "opened_at_ns"))
    return [from_rows(core, by_signal.get(as_str(core, "signal_id"), [])) for core in cores]


def read_signal(
    core_table: IcebergTable, transitions_table: IcebergTable, signal_id: uuid.UUID
) -> Candidate | None:
    wanted = str(signal_id)
    for core in core_table.read().to_pylist():
        if as_str(core, "signal_id") != wanted:
            continue
        transitions = [
            row
            for row in transitions_table.read().to_pylist()
            if as_str(row, "signal_id") == wanted
        ]
        return from_rows(core, transitions)
    return None
