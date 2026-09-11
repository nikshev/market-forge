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

SECOND = 1_000_000_000


def _env() -> dict[str, str]:
    """The stack's settings, from `.env` or `.env.example`.

    A fresh checkout has no `.env` yet, and the failure should be "the stack is
    not running" rather than "no configuration".
    """
    values: dict[str, str] = {}
    for name in (".env", ".env.example"):
        path = Path(__file__).resolve().parents[2] / name
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values.setdefault(key.strip(), value.strip())
        break
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
    from pyiceberg.catalog.sql import SqlCatalog

    env = _env()
    store = SqlCatalog(
        "channelflow",
        uri=f"sqlite:///{tmp_path}/catalog.db",
        warehouse=f"s3://{env['MINIO_BUCKET']}/iceberg-test/{uuid.uuid4()}",
        **{
            "s3.endpoint": f"http://127.0.0.1:{env['MINIO_PORT']}",
            "s3.access-key-id": env["MINIO_ROOT_USER"],
            "s3.secret-access-key": env["MINIO_ROOT_PASSWORD"],
        },
    )
    try:
        store.create_namespace("channelflow")
    except Exception as exc:  # noqa: BLE001 -- the stack being down is the
        # failure worth naming, and it arrives as whatever the client raises.
        pytest.fail(f"Object store is not answering: {exc}. Run `make up`.")
    return store


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
