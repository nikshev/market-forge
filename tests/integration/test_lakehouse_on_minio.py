"""The canonical plane against a real object store (REQ-STORE-001, REQ-WP-039).

The unit tests run against a SQLite catalog and a local warehouse. These run
against MinIO, because [[ADR-002]] made S3-compatible object storage the
canonical plane precisely so local and production would not diverge -- and that
is only true if something checks the real thing, which is what CLAUDE.md means
by "CI is where `implemented` is earned".

What a local warehouse cannot prove: that `pyiceberg`'s FileIO reaches this
backend at all, that a commit's metadata round-trips through it, and that a
point-in-time read still answers correctly when every file it names lives behind
an S3 API rather than a filesystem.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from channelflow.lakehouse import Column, IcebergTable, Schema
from channelflow.lakehouse import catalog as open_catalog

SECOND = 1_000_000_000


def _env() -> dict[str, str]:
    """The stack's settings, from `.env` or `.env.example`.

    A fresh checkout has no `.env` yet, and the failure should be "the stack is
    not running" rather than "no configuration".
    """
    values: dict[str, str] = {}
    # `.env.example` first as the documented defaults, `.env` over it as the
    # developer's overrides. An earlier version read whichever existed and
    # stopped, so a key added to the example -- a new service, say -- was
    # missing on every checkout whose `.env` predated it, and the failure said
    # `KeyError` rather than "copy the new line".
    for name in (".env.example", ".env"):
        path = Path(__file__).resolve().parents[2] / name
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    values.update({k: v for k, v in os.environ.items() if k in values})
    return values


@pytest.fixture
def catalog(tmp_path: Path) -> object:
    """A catalog whose warehouse is the real bucket.

    The catalog itself is SQLite in a temp directory: what is under test is the
    storage, not where the pointer lives. A fresh prefix per test, because these
    write real objects and a reused one would read another run's snapshots and
    pass for the wrong reason.
    """
    env = _env()
    try:
        # The same factory the fast gate uses, with a different warehouse. A
        # test that built its own catalog would prove the storage and not the
        # claim ([[ADR-060]], [[REQ-WP-041]]).
        return open_catalog(
            uri=f"sqlite:///{tmp_path}/catalog.db",
            warehouse=f"s3://{env['MINIO_BUCKET']}/iceberg-test/{uuid.uuid4()}",
            **{
                "s3.endpoint": f"http://127.0.0.1:{env['MINIO_PORT']}",
                "s3.access-key-id": env["MINIO_ROOT_USER"],
                "s3.secret-access-key": env["MINIO_ROOT_PASSWORD"],
            },
        )
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"Object store is not answering: {exc}. Run `make up`.")


def _schema() -> Schema:
    return Schema(
        columns=(
            Column(name="event_time_ns", type="timestamp_ns"),
            Column(name="symbol", type="string"),
            Column(name="price", type="float64"),
        ),
        event_time_column="event_time_ns",
    )


def _row(index: int) -> dict[str, object]:
    return {"event_time_ns": index * SECOND, "symbol": "BTCUSDT", "price": 50_000.0 + index}


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.trace("REQ-WP-039")
def test_a_table_commits_reads_and_time_travels_on_a_real_object_store(
    catalog: object,
) -> None:
    """The whole round trip, against the store [[ADR-002]] chose."""
    table = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]

    first = table.append([_row(1), _row(2)])
    table.append([_row(3)])

    assert table.snapshot_ids() == (1, 2)
    assert table.read(snapshot_id=1).num_rows == 2
    assert table.read().num_rows == 3
    assert table.read(as_of_ns=2 * SECOND).num_rows == 2
    assert table.snapshot(1).content_hash == first.content_hash


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.trace("REQ-WP-039")
def test_rows_come_back_in_commit_order_from_the_real_store(catalog: object) -> None:
    """The guarantee the migration nearly reversed in silence, checked where the
    file listing is a real listing."""
    table = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]
    for index in (1, 2, 3):
        table.append([_row(index)])

    assert table.read()["event_time_ns"].to_pylist() == [SECOND, 2 * SECOND, 3 * SECOND]


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.trace("REQ-WP-039")
def test_an_earlier_read_is_unchanged_by_a_later_commit(catalog: object) -> None:
    """Point-in-time safety is the reason the plane exists, so it is checked
    against the storage it actually runs on."""
    table = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]
    table.append([_row(1), _row(2)])
    before = table.read(snapshot_id=1).num_rows

    table.append([_row(3)])

    assert table.read(snapshot_id=1).num_rows == before


# --------------------------------------------------------------------------
# Maintenance, where it runs (REQ-WP-070)
# --------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-070")
def test_unreferenced_files_are_found_on_an_object_store(catalog: object) -> None:
    """The gap that let a no-op survive.

    `unreferenced_files` walked the table's location with `Path.is_dir()`, which
    is false for `s3://…`, so it returned nothing — and retention deleted nothing
    while reporting `files_removed=0`, which is what it also reports when there
    is genuinely nothing to delete.

    Every test of it ran against a local warehouse, where the walk works. This
    is the one that runs where the data is.
    """
    table = IcebergTable(
        name=f"orphans_{uuid.uuid4().hex[:8]}",
        schema=Schema(columns=(Column(name="n", type="int64"),)),
        catalog=catalog,  # type: ignore[arg-type]
    )
    for n in range(6):
        table.append([{"n": n}])

    assert table.unreferenced_files() == (), "nothing is orphaned before a compaction"

    # Compaction alone orphans nothing: the files it replaced are still named by
    # the snapshots that wrote them. They become orphans when those go.
    table.compact()
    assert table.unreferenced_files() == ()

    table.expire_snapshots_except([table.snapshot_ids()[-1]])

    orphans = table.unreferenced_files()
    assert len(orphans) == 6, "the walk found the files no live snapshot names"
    assert all(path.startswith("s3://") for path in orphans)


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-070")
def test_a_maintenance_pass_frees_objects_and_keeps_the_rows(catalog: object) -> None:
    """What the pass is for, end to end, against the real store."""
    from channelflow.lakehouse import maintenance
    from channelflow.lakehouse.retention import RetentionPolicy

    table = IcebergTable(
        name=f"maintained_{uuid.uuid4().hex[:8]}",
        schema=Schema(
            columns=(Column(name="at_ns", type="timestamp_ns"), Column(name="n", type="int64")),
            event_time_column="at_ns",
        ),
        catalog=catalog,  # type: ignore[arg-type]
    )
    base = 1_700_000_000 * SECOND
    for n in range(8):
        table.append([{"at_ns": base + n * SECOND, "n": n}])
    before = table.read().to_pylist()

    report = maintenance.run(
        table,
        policy=RetentionPolicy(keep_ns=10_000 * 365 * 24 * 3600 * SECOND),
        now_ns=base + 100 * SECOND,
    )

    assert report.files_before == 8
    assert report.retention is not None
    assert report.retention.files_removed == 8, "the objects compaction replaced are gone"
    assert table.read().to_pylist() == before, "every row survived, in order"
    assert table.unreferenced_files() == ()


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-070")
def test_a_location_that_cannot_be_listed_is_refused(catalog: object) -> None:
    """An empty answer from the walk reads as 'nothing is orphaned'. When the
    walk cannot look, it must say so instead."""
    from channelflow.lakehouse.iceberg import CannotList, _walk

    with pytest.raises(CannotList, match="cannot enumerate"):
        _walk("s3://bucket/prefix", io=None)
