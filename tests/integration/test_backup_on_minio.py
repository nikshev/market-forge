"""The backup round trip against a real object store (REQ-WP-037).

A backup is the one feature whose failure is discovered only when it is needed,
so it is checked against the backend it will actually run on.

[[ADR-061]]: a restore lands where the backup came from, because Iceberg's
metadata holds absolute URIs. Here that means the bucket prefix the table was
written to, which is what a bucket restored under its own name gives back.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from channelflow.lakehouse import Column, IcebergTable, Schema, back_up, verify

SECOND = 1_000_000_000


def _env() -> dict[str, str]:
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
    from pyiceberg.catalog.sql import SqlCatalog

    env = _env()
    store = SqlCatalog(
        "channelflow",
        uri=f"sqlite:///{tmp_path}/catalog.db",
        warehouse=f"s3://{env['MINIO_BUCKET']}/backup-test/{uuid.uuid4()}",
        **{
            "s3.endpoint": f"http://127.0.0.1:{env['MINIO_PORT']}",
            "s3.access-key-id": env["MINIO_ROOT_USER"],
            "s3.secret-access-key": env["MINIO_ROOT_PASSWORD"],
        },
    )
    try:
        store.create_namespace("channelflow")
    except Exception as exc:  # noqa: BLE001
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
@pytest.mark.trace("REQ-WP-037")
def test_a_table_on_the_real_store_verifies_whole(catalog: object) -> None:
    """Every file every snapshot names, present, with a real listing behind the
    check rather than a directory walk."""
    table = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]
    table.append([_row(1), _row(2)])
    table.append([_row(3)])

    assert verify(table).ok


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-037")
def test_a_table_in_the_bucket_backs_up_and_restores(catalog: object, tmp_path: Path) -> None:
    """The round trip where it matters.

    The first version of this copied files with `shutil`, which works against a
    local warehouse and cannot see an `s3://` path at all -- a backup that did
    not back up the storage the system actually uses. It reads and writes
    through Iceberg's own `FileIO` now, which is the same client the table
    commits through.
    """
    from pyiceberg.exceptions import NoSuchTableError

    from channelflow.lakehouse import restore

    table = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]
    table.append([_row(1), _row(2)])
    table.append([_row(3)])
    before = table.read().to_pylist()

    back_up(table, target=tmp_path / "backup")

    # The catalog forgets the table; the objects stay where they are, which is
    # where a restore puts them back ([[ADR-061]]).
    catalog.drop_table("channelflow.cex_trades")  # type: ignore[attr-defined]
    with pytest.raises(NoSuchTableError):
        catalog.load_table("channelflow.cex_trades")  # type: ignore[attr-defined]

    restore("cex_trades", backup=tmp_path / "backup", catalog=catalog)

    restored = IcebergTable(name="cex_trades", schema=_schema(), catalog=catalog)  # type: ignore[arg-type]
    assert restored.read().to_pylist() == before
    assert restored.snapshot_ids() == (1, 2)
