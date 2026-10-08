"""The notary's four append-only tables (REQ-INFRA-007).

# @trace: REQ-INFRA-007

Nothing here is updated. A record is registered once; a batch is formed once; what happens to a
batch is a sequence of events, and its state is **the latest event about it**. The outbox is
therefore a query, not a column that something has to remember to keep true: the previous
design for this (a mutable status) is a second way to edit history, and Principle III exists to
keep the first one.

Column meanings and the time each carries are in `specs/143-notarize-final-records/data-model.md`.
"""

from __future__ import annotations

from collections.abc import Iterable

from channelflow.lakehouse import Catalog, Column, IcebergTable, Schema

RECORDS = "notary_records"
BATCHES = "notary_batches"
LEAVES = "notary_leaves"
EVENTS = "notary_events"

RECORDS_SCHEMA = Schema(
    columns=(
        Column(name="bar_close_time_ns", type="timestamp_ns"),
        Column(name="record_id", type="string"),
        Column(name="kind", type="string"),
        Column(name="venue", type="string"),
        Column(name="symbol", type="string"),
        Column(name="timeframe_ns", type="int64"),
        Column(name="record_hash", type="string"),
        Column(name="record_bytes", type="string"),
        Column(name="scheme_version", type="int64"),
        Column(name="config_hash", type="string"),
        Column(name="dataset_ref", type="string"),
        Column(name="dataset_snapshot_id", type="int64"),
        Column(name="code_commit", type="string"),
        Column(name="notarizable", type="string"),
        Column(name="reason", type="string"),
        #: `ingest_time`-class: when the registrar wrote it. Informational; never hashed.
        Column(name="registered_at_ns", type="int64"),
    ),
    event_time_column="bar_close_time_ns",
)

BATCHES_SCHEMA = Schema(
    columns=(
        Column(name="max_bar_close_time_ns", type="timestamp_ns"),
        Column(name="batch_root", type="string"),
        Column(name="leaf_count", type="int64"),
        Column(name="min_bar_close_time_ns", type="int64"),
        Column(name="formed_at_ns", type="int64"),
        Column(name="window_ns", type="int64"),
    ),
    event_time_column="max_bar_close_time_ns",
)

LEAVES_SCHEMA = Schema(
    columns=(
        Column(name="bar_close_time_ns", type="timestamp_ns"),
        Column(name="batch_root", type="string"),
        Column(name="ordinal", type="int64"),
        Column(name="record_id", type="string"),
        Column(name="record_hash", type="string"),
    ),
    event_time_column="bar_close_time_ns",
)

EVENTS_SCHEMA = Schema(
    columns=(
        Column(name="event_at_ns", type="timestamp_ns"),
        Column(name="batch_root", type="string"),
        Column(name="event", type="string"),
        Column(name="attempt", type="int64"),
        Column(name="tx_hash", type="string"),
        Column(name="nonce", type="int64"),
        Column(name="block_number", type="int64"),
        #: The chain's own time, seconds (`block_time`), for `confirmed`; -1 otherwise.
        Column(name="block_time_s", type="int64"),
        Column(name="detail", type="string"),
    ),
    event_time_column="event_at_ns",
)

Row = dict[str, object]


def records_table(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=RECORDS, schema=RECORDS_SCHEMA, catalog=catalog)


def batches_table(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=BATCHES, schema=BATCHES_SCHEMA, catalog=catalog)


def leaves_table(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=LEAVES, schema=LEAVES_SCHEMA, catalog=catalog)


def events_table(catalog: Catalog) -> IcebergTable:
    return IcebergTable(name=EVENTS, schema=EVENTS_SCHEMA, catalog=catalog)


def registered_ids(table: IcebergTable) -> set[str]:
    """Every record id already registered: read once per pass, not per series."""
    return {str(r["record_id"]) for r in table.read().to_pylist()}


def _order(row: Row) -> tuple[int, str, str]:
    return (int(str(row["bar_close_time_ns"])), str(row["kind"]), str(row["record_id"]))


def unbatched(records: IcebergTable, leaves: IcebergTable) -> list[Row]:
    """Notarizable records that are in no batch yet, in the order a batch is built."""
    batched = {str(r["record_id"]) for r in leaves.read().to_pylist()}
    waiting = [
        r
        for r in records.read().to_pylist()
        if r["notarizable"] == "yes" and str(r["record_id"]) not in batched
    ]
    return sorted(waiting, key=_order)


def unnotarizable(records: IcebergTable) -> list[Row]:
    return sorted((r for r in records.read().to_pylist() if r["notarizable"] == "no"), key=_order)


def batch_states(events: IcebergTable) -> dict[str, Row]:
    """The latest event of every batch. Ties on time are broken by append order."""
    latest: dict[str, tuple[tuple[int, int], Row]] = {}
    for position, row in enumerate(events.read().to_pylist()):
        key = (int(str(row["event_at_ns"])), position)
        root = str(row["batch_root"])
        if root not in latest or key >= latest[root][0]:
            latest[root] = (key, row)
    return {root: row for root, (_, row) in latest.items()}


def unconfirmed(events: IcebergTable) -> list[Row]:
    return sorted(
        (r for r in batch_states(events).values() if r["event"] != "confirmed"),
        key=lambda r: int(str(r["event_at_ns"])),
    )


def append_rows(table: IcebergTable, rows: Iterable[Row]) -> int:
    batch = list(rows)
    if batch:
        table.append(batch)
    return len(batch)


def event_row(
    batch_root: str,
    event: str,
    *,
    at_ns: int,
    attempt: int = 0,
    tx_hash: str = "",
    nonce: int = -1,
    block_number: int = -1,
    block_time_s: int = -1,
    detail: str = "",
) -> Row:
    """One entry of the outbox log; the fields an event does not use carry explicit absences."""
    return {
        "event_at_ns": at_ns,
        "batch_root": batch_root,
        "event": event,
        "attempt": attempt,
        "tx_hash": tx_hash,
        "nonce": nonce,
        "block_number": block_number,
        "block_time_s": block_time_s,
        "detail": detail,
    }
