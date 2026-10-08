# @trace: REQ-INFRA-007
"""The pass with the notary attached: same output, one pinned input, never a reason to stop."""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.notary import tables as notary_tables
from channelflow.notary.config import WorkerNotary
from channelflow.pipeline import channel_main
from channelflow.tables import bars as bars_table
from channelflow.tables import channels as channels_table
from channelflow.tables import extrema as extrema_table
from channelflow.tables import signals as signals_table
from channelflow.timeframes import TIMEFRAMES
from tests.unit.pipeline.test_replay import rising_with_rejections

COMMIT = "0123456789abcdef0123456789abcdef01234567"
NOTARY = WorkerNotary(from_ns=0, code_commit=COMMIT, code_dirty="false")


def plane(home: Path) -> Catalog:
    home.mkdir(parents=True, exist_ok=True)
    catalog = open_catalog(uri=f"sqlite:///{home}/catalog.db", warehouse=str(home))
    bars_table.write_bars(bars_table.table_for(catalog), rising_with_rejections())
    return catalog


def outputs(catalog: Catalog) -> dict[str, list[dict[str, object]]]:
    """Everything a pass writes, canonically ordered so two planes can be compared."""
    tables = {
        "channels": channels_table.table_for(catalog),
        "signals": signals_table.table_for(catalog),
        "transitions": signals_table.transitions_table_for(catalog),
        "confirmed": extrema_table.confirmed_table_for(catalog),
        "candidates": extrema_table.candidates_table_for(catalog),
    }
    return {
        name: sorted(table.read().to_pylist(), key=lambda r: repr(sorted(r.items())))
        for name, table in tables.items()
    }


def run(catalog: Catalog, *, notary: WorkerNotary | None) -> None:
    channel_main.run_pass(catalog, targets=[TIMEFRAMES["1m"]], notary=notary, gap_threshold=1)


@pytest.mark.trace("REQ-INFRA-007")
def test_the_pass_writes_exactly_the_same_with_the_notary_attached(tmp_path: Path) -> None:
    without = plane(tmp_path / "without")
    with_notary = plane(tmp_path / "with")

    run(without, notary=None)
    run(with_notary, notary=NOTARY)

    assert outputs(with_notary) == outputs(without)
    assert notary_tables.records_table(with_notary).read().num_rows > 0
    assert notary_tables.records_table(without).read().num_rows == 0


@pytest.mark.trace("REQ-INFRA-007")
def test_every_read_of_the_pass_uses_the_one_pinned_bars_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = plane(tmp_path / "pinned")
    pinned = bars_table.table_for(catalog).current()
    assert pinned is not None
    seen: list[int | None] = []
    real = bars_table.read_bars

    def spy(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        seen.append(kwargs.get("snapshot_id"))  # type: ignore[arg-type]
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(channel_main.bars_table, "read_bars", spy)
    run(catalog, notary=NOTARY)

    assert seen and set(seen) == {pinned.snapshot_id}
    rows = notary_tables.records_table(catalog).read().to_pylist()
    assert {r["dataset_snapshot_id"] for r in rows} == {pinned.snapshot_id}


@pytest.mark.trace("REQ-INFRA-007")
def test_a_second_cycle_registers_nothing_new(tmp_path: Path) -> None:
    catalog = plane(tmp_path / "again")
    run(catalog, notary=NOTARY)
    first = notary_tables.records_table(catalog).read().num_rows

    run(catalog, notary=NOTARY)

    assert notary_tables.records_table(catalog).read().num_rows == first


@pytest.mark.trace("REQ-INFRA-007")
def test_a_registration_that_fails_does_not_change_or_stop_the_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    reference = plane(tmp_path / "reference")
    run(reference, notary=None)

    broken = plane(tmp_path / "broken")

    def refuse(*args: object, **kwargs: object) -> int:
        raise OSError("the object store is unreachable")

    monkeypatch.setattr(notary_tables, "append_rows", refuse)
    run(broken, notary=NOTARY)  # must not raise

    assert outputs(broken) == outputs(reference)
    out = capsys.readouterr().out
    assert "notary" in out and "unreachable" in out


@pytest.mark.trace("REQ-INFRA-007")
def test_a_pass_without_a_usable_commit_stores_unnotarizable_records_and_still_runs(
    tmp_path: Path,
) -> None:
    catalog = plane(tmp_path / "nocommit")
    run(catalog, notary=WorkerNotary(from_ns=0, code_commit=None, code_dirty=None))

    rows = notary_tables.records_table(catalog).read().to_pylist()
    assert rows and {r["notarizable"] for r in rows} == {"no"}
    assert channels_table.table_for(catalog).read().num_rows > 0


class _Counter:
    """Counts every lakehouse read and append a pass makes, by table."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from channelflow.lakehouse import IcebergTable

        self.reads: dict[str, int] = {}
        self.appends: dict[str, int] = {}
        real_read, real_append = IcebergTable.read, IcebergTable.append

        def read(table, *args, **kwargs):  # type: ignore[no-untyped-def]
            self.reads[table.name] = self.reads.get(table.name, 0) + 1
            return real_read(table, *args, **kwargs)

        def append(table, rows):  # type: ignore[no-untyped-def]
            self.appends[table.name] = self.appends.get(table.name, 0) + 1
            return real_append(table, rows)

        monkeypatch.setattr(IcebergTable, "read", read)
        monkeypatch.setattr(IcebergTable, "append", append)


@pytest.mark.trace("REQ-INFRA-007")
def test_the_notary_adds_one_read_to_a_pass_and_no_read_of_any_other_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-003, in operations rather than seconds. The pass already replays the whole history and
    reads whole tables for every series (research R12); the notary must not add to that. A timing
    comparison would be noise against passes that vary by 25 %; the count of reads cannot be."""
    without, with_notary = plane(tmp_path / "w0"), plane(tmp_path / "w1")
    plain = _Counter(monkeypatch)
    run(without, notary=None)
    baseline_reads, baseline_appends = dict(plain.reads), dict(plain.appends)

    attached = _Counter(monkeypatch)
    run(with_notary, notary=NOTARY)

    notary_names = {"notary_records", "notary_batches", "notary_leaves", "notary_events"}
    other_reads = {k: v for k, v in attached.reads.items() if k not in notary_names}
    assert other_reads == baseline_reads  # not one extra read of any table the pass already read
    assert attached.reads.get("notary_records", 0) <= 1
    assert not (set(attached.reads) & (notary_names - {"notary_records"}))
    assert {k: v for k, v in attached.appends.items() if k not in notary_names} == baseline_appends
    # One commit per (series, timeframe) that had something to register -- here, one series.
    assert attached.appends.get("notary_records", 0) <= 1


@pytest.mark.trace("REQ-INFRA-007")
def test_a_real_pass_through_an_outage_and_back_every_record_is_committed_once_and_provable(
    tmp_path: Path,
) -> None:
    """The whole path on real data: pass -> registration -> batch -> a chain that is down -> a chain
    that is up. Signals were produced (the pass never touched the chain); each record's inclusion
    proof verifies against the root that reached the chain; its hash recomputes from what was
    stored."""
    from channelflow.notary.scheme import (
        Context,
        inclusion_proof,
        record_hash_hex,
        verify_inclusion,
    )
    from channelflow.notary.submitter import Submitter, SubmitterConfig, outbox_summary
    from tests.notary.conftest import SECOND, FakeNotaryChain

    catalog = plane(tmp_path / "e2e")
    run(catalog, notary=NOTARY)
    produced = outputs(catalog)
    assert produced["channels"] and produced["transitions"]

    records = notary_tables.records_table(catalog).read().to_pylist()
    last_registered = max(int(r["registered_at_ns"]) for r in records)
    window = 30 * 60 * SECOND
    clock = [last_registered + window]
    chain = FakeNotaryChain(down=True)
    sub = Submitter(
        catalog=catalog,
        chain=chain,
        config=SubmitterConfig(
            window_ns=window,
            max_batch=10_000,
            min_balance_wei=10**17,
            max_gas_price_wei=500 * 10**9,
            submit_timeout_ns=120 * SECOND,
        ),
        now_ns=lambda: clock[0],
    )

    sub.tick()
    down = outbox_summary(catalog, now_ns=clock[0])
    assert down.unconfirmed_batches >= 1 and "connection refused" in down.last_error
    assert chain.sent == [] and outputs(catalog) == produced  # nothing lost, nothing changed

    chain.down = False
    sub.tick()
    assert outbox_summary(catalog, now_ns=clock[0]).unconfirmed_batches == 0
    assert len(chain.sent) == down.unconfirmed_batches  # each batch once

    leaves = notary_tables.leaves_table(catalog).read().to_pylist()
    committed_roots = {root.hex() for root, _ in chain.sent}
    assert {leaf["batch_root"] for leaf in leaves} == committed_roots
    assert len(leaves) == len(records)  # every record is in exactly one batch
    for root in committed_roots:
        batch_leaves = sorted(
            (leaf for leaf in leaves if leaf["batch_root"] == root), key=lambda x: x["ordinal"]
        )
        hashes = [bytes.fromhex(str(leaf["record_hash"])) for leaf in batch_leaves]
        for leaf in batch_leaves:
            index = int(leaf["ordinal"])
            proof = inclusion_proof(hashes, index)
            assert verify_inclusion(hashes[index], index, len(hashes), proof, bytes.fromhex(root))
    by_id = {r["record_id"]: r for r in records}
    for leaf in leaves:
        row = by_id[leaf["record_id"]]
        context = Context(str(row["config_hash"]), str(row["dataset_ref"]), str(row["code_commit"]))
        recomputed = record_hash_hex(
            str(row["kind"]), bytes.fromhex(str(row["record_bytes"])), context
        )
        assert recomputed == leaf["record_hash"]
