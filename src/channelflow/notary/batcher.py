"""Forming a batch: when a window closes, and what a batch is (REQ-INFRA-007).

# @trace: REQ-INFRA-007

A batch is a list of records in a fixed order and the root over their hashes. Its root *is* its
identity: the leaves are written before anything is sent, a retry re-sends the same root, and a
batch is never re-formed (a different root for the same records would orphan the first).

The window is measured on the time a record entered the outbox -- a scheduling decision, taken
from the local clock. It is never part of a claim: the latency the product states is the chain's
block time minus the record's bar close, and neither is the local clock.

The three appends are separate commits, in an order chosen so that a crash between any two can be
repaired: leaves, then the batch row, then the `formed` event. See `repair_orphans`.
"""

from __future__ import annotations

from dataclasses import dataclass

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.scheme import merkle_root

SECOND_NS = 1_000_000_000


class NotWholeSecond(ValueError):
    """A bar close that is not a whole second cannot be committed as the contract's `barTs`."""


@dataclass(frozen=True)
class Leaf:
    record_id: str
    record_hash: bytes
    bar_close_time_ns: int
    ordinal: int


@dataclass(frozen=True)
class Batch:
    root: bytes
    leaves: tuple[Leaf, ...]
    min_bar_close_time_ns: int
    max_bar_close_time_ns: int
    formed_at_ns: int
    window_ns: int

    @property
    def bar_ts_s(self) -> int:
        """The contract's `barTs`: the latest leaf bar close, in whole seconds."""
        return self.max_bar_close_time_ns // SECOND_NS


def form_batch(catalog: Catalog, *, now_ns: int, window_ns: int, max_batch: int) -> Batch | None:
    waiting = tables.unbatched(tables.records_table(catalog), tables.leaves_table(catalog))
    if not waiting:
        return None
    oldest = min(int(str(r["registered_at_ns"])) for r in waiting)
    if now_ns - oldest < window_ns:
        return None

    chosen = waiting[:max_batch]
    for row in chosen:
        if int(str(row["bar_close_time_ns"])) % SECOND_NS:
            raise NotWholeSecond(
                f"{row['record_id']}: bar close {row['bar_close_time_ns']} ns is not a whole second"
            )

    leaves = tuple(
        Leaf(
            record_id=str(row["record_id"]),
            record_hash=bytes.fromhex(str(row["record_hash"])),
            bar_close_time_ns=int(str(row["bar_close_time_ns"])),
            ordinal=ordinal,
        )
        for ordinal, row in enumerate(chosen)
    )
    root = merkle_root([leaf.record_hash for leaf in leaves])
    batch = Batch(
        root=root,
        leaves=leaves,
        min_bar_close_time_ns=min(leaf.bar_close_time_ns for leaf in leaves),
        max_bar_close_time_ns=max(leaf.bar_close_time_ns for leaf in leaves),
        formed_at_ns=now_ns,
        window_ns=window_ns,
    )
    write_batch(catalog, batch)
    return batch


def write_leaves(catalog: Catalog, batch: Batch) -> None:
    """The first append: the records become 'batched'. Atomic -- all the leaves or none."""
    tables.append_rows(
        tables.leaves_table(catalog),
        (
            {
                "bar_close_time_ns": leaf.bar_close_time_ns,
                "batch_root": batch.root.hex(),
                "ordinal": leaf.ordinal,
                "record_id": leaf.record_id,
                "record_hash": leaf.record_hash.hex(),
            }
            for leaf in batch.leaves
        ),
    )


def write_batch(catalog: Catalog, batch: Batch) -> None:
    """Leaves first, then the batch, then the event. Each append is atomic; see `repair_orphans`."""
    write_leaves(catalog, batch)
    append_batch_row(catalog, batch)


def repair_orphans(catalog: Catalog, *, now_ns: int, window_ns: int) -> int:
    """Complete a batch whose leaves were written and whose batch row was not (a crash between).

    Without this the records would be 'batched' into nothing and never sent. The root is a function
    of the leaves, so the batch is rebuilt from them and accepted only if it hashes to the root the
    leaves carry; anything else is left alone, because guessing would be worse than waiting.
    """
    known = {str(r["batch_root"]) for r in tables.batches_table(catalog).read().to_pylist()}
    by_root: dict[str, list[tables.Row]] = {}
    for row in tables.leaves_table(catalog).read().to_pylist():
        root = str(row["batch_root"])
        if root not in known:
            by_root.setdefault(root, []).append(row)

    repaired = 0
    for root, rows in by_root.items():
        ordered = sorted(rows, key=lambda r: int(str(r["ordinal"])))
        if [int(str(r["ordinal"])) for r in ordered] != list(range(len(ordered))):
            continue
        leaves = tuple(
            Leaf(
                record_id=str(r["record_id"]),
                record_hash=bytes.fromhex(str(r["record_hash"])),
                bar_close_time_ns=int(str(r["bar_close_time_ns"])),
                ordinal=int(str(r["ordinal"])),
            )
            for r in ordered
        )
        if merkle_root([leaf.record_hash for leaf in leaves]).hex() != root:
            continue
        append_batch_row(
            catalog,
            Batch(
                root=bytes.fromhex(root),
                leaves=leaves,
                min_bar_close_time_ns=min(leaf.bar_close_time_ns for leaf in leaves),
                max_bar_close_time_ns=max(leaf.bar_close_time_ns for leaf in leaves),
                formed_at_ns=now_ns,
                window_ns=window_ns,
            ),
        )
        repaired += 1
    return repaired


def append_batch_row(catalog: Catalog, batch: Batch) -> None:
    tables.append_rows(
        tables.batches_table(catalog),
        [
            {
                "max_bar_close_time_ns": batch.max_bar_close_time_ns,
                "batch_root": batch.root.hex(),
                "leaf_count": len(batch.leaves),
                "min_bar_close_time_ns": batch.min_bar_close_time_ns,
                "formed_at_ns": batch.formed_at_ns,
                "window_ns": batch.window_ns,
            }
        ],
    )
    tables.append_rows(
        tables.events_table(catalog),
        [tables.event_row(batch.root.hex(), "formed", at_ns=batch.formed_at_ns)],
    )
