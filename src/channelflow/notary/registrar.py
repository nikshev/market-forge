"""Registering what a pass computes, by identity (REQ-INFRA-007).

# @trace: REQ-INFRA-007

The registrar subscribes to the events a replay already publishes. It needs no change to
`replay.py`, and it cannot lose a record to a crash: the pass replays the whole bar history every
cycle and `record_replay` skips what it has already written, but the bus still fires for all of
it, so a record whose lakehouse write succeeded and whose registration did not is simply
registered on the next cycle. Identity -- not time -- decides what is new: a record whose id is
already registered is left alone, however the dataset reference has moved since, so a record is
committed at most once (FR-006).

It touches no chain and no key. If the lakehouse refuses its append the exception goes to the
caller, which logs it and carries on: the notary is never a reason a pass stops.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from channelflow.events import CandidateUpdated, ChannelFitted
from channelflow.lakehouse import IcebergTable
from channelflow.notary import tables
from channelflow.notary.context import NotaryContext
from channelflow.notary.records import NotFinal, Record, decision_records, snapshot_record
from channelflow.notary.scheme import SCHEME_VERSION, record_hash_hex


@dataclass
class Registrar:
    records_table: IcebergTable
    context: NotaryContext
    #: The epoch: records whose bar closed before it are not registered (no backfill).
    from_ns: int
    #: Ids already registered, read once per pass and extended as records are added.
    registered: set[str] = field(default_factory=set)
    now_ns: Callable[[], int] = time.time_ns
    #: Refused for not being final or for having seen the future: counted, never registered.
    refused: int = 0
    last_refusal: str = ""
    _pending: list[Record] = field(default_factory=list)

    def snapshot_handler(
        self, venue: str, symbol: str, timeframe_ns: int
    ) -> Callable[[ChannelFitted], None]:
        def handle(event: ChannelFitted) -> None:
            snapshot = event.snapshot
            if snapshot.as_of_ns < self.from_ns:
                return
            record_id = f"snapshot|{venue}|{symbol}|{timeframe_ns}|{snapshot.as_of_ns}"
            if record_id in self.registered:
                return
            try:
                record = snapshot_record(
                    snapshot,
                    venue=venue,
                    symbol=symbol,
                    timeframe_ns=timeframe_ns,
                    bar_final=event.bar.is_final,
                )
            except NotFinal as error:
                self.refused += 1
                self.last_refusal = str(error)
                return
            self._add(record)

        return handle

    def decision_handler(self) -> Callable[[CandidateUpdated], None]:
        def handle(event: CandidateUpdated) -> None:
            for record in decision_records(event.candidate):
                if record.bar_close_time_ns < self.from_ns or record.record_id in self.registered:
                    continue
                self._add(record)

        return handle

    def _add(self, record: Record) -> None:
        self.registered.add(record.record_id)
        self._pending.append(record)

    @property
    def pending(self) -> int:
        return len(self._pending)

    def flush(self) -> int:
        """Append everything pending in one commit; returns how many rows."""
        if not self._pending:
            return 0
        registered_at = self.now_ns()
        ctx = self.context
        rows: list[tables.Row] = []
        for record in self._pending:
            hashed = (
                record_hash_hex(record.kind, record.data, ctx.as_scheme())
                if ctx.notarizable
                else ""
            )
            rows.append(
                {
                    "bar_close_time_ns": record.bar_close_time_ns,
                    "record_id": record.record_id,
                    "kind": record.kind,
                    "venue": record.venue,
                    "symbol": record.symbol,
                    "timeframe_ns": record.timeframe_ns,
                    "record_hash": hashed,
                    "record_bytes": record.data.hex(),
                    "scheme_version": SCHEME_VERSION,
                    "config_hash": ctx.config_hash,
                    "dataset_ref": ctx.dataset_ref,
                    "dataset_snapshot_id": ctx.dataset_snapshot_id,
                    "code_commit": ctx.code_commit,
                    "notarizable": "yes" if ctx.notarizable else "no",
                    "reason": ctx.reason or "",
                    "registered_at_ns": registered_at,
                }
            )
        count = tables.append_rows(self.records_table, rows)
        self._pending.clear()
        return count
