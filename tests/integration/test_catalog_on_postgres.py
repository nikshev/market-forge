"""The catalog on the stack's own database (REQ-WP-041).

[[ADR-060]] said the catalog is one implementation, SQLite locally and
PostgreSQL on the stack, differing only in a URL -- and that claim is what keeps
REQ-INFRA-002's "a commit needs no running service" compatible with a plane that
needs a catalog at all. Every other test opens SQLite, so until this file
existed the claim was a sentence in a document.

[[ADR-002]] reasoned the same way about storage and chose MinIO over a local
directory rather than accept the gap. This is that decision applied to where the
pointer lives.
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
def stack_catalog() -> object:
    """A catalog whose pointer lives in the stack's PostgreSQL.

    Opened by the same factory the fast gate uses against SQLite: if this file
    needed a different function, the thing [[ADR-060]] claimed would be false.

    The warehouse is the real bucket, because a catalog pointing at somewhere
    the data is not would prove half a sentence.
    """
    env = _env()
    dsn = (
        f"postgresql+psycopg://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}"
        f"@127.0.0.1:{env['POSTGRES_PORT']}/{env['POSTGRES_DB']}"
    )
    warehouse = f"s3://{env['MINIO_BUCKET']}/catalog-test/{uuid.uuid4()}"
    try:
        return open_catalog(
            uri=dsn,
            warehouse=warehouse,
            **{
                "s3.endpoint": f"http://127.0.0.1:{env['MINIO_PORT']}",
                "s3.access-key-id": env["MINIO_ROOT_USER"],
                "s3.secret-access-key": env["MINIO_ROOT_PASSWORD"],
            },
        )
    except Exception as exc:  # noqa: BLE001 -- the stack being down is the
        # failure worth naming, and it arrives as whatever the driver raises.
        pytest.fail(f"The stack's PostgreSQL is not answering: {exc}. Run `make up`.")


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
@pytest.mark.trace("REQ-WP-041")
def test_a_table_commits_reads_and_time_travels_through_the_stack_catalog(
    stack_catalog: object,
) -> None:
    """The whole claim, against the database it was made about."""
    table = IcebergTable(
        name=f"cex_trades_{uuid.uuid4().hex[:8]}",
        schema=_schema(),
        catalog=stack_catalog,  # type: ignore[arg-type]
    )

    first = table.append([_row(1), _row(2)])
    table.append([_row(3)])

    assert table.snapshot_ids() == (1, 2)
    assert table.read(snapshot_id=1).num_rows == 2
    assert table.read().num_rows == 3
    assert table.read(as_of_ns=2 * SECOND).num_rows == 2
    assert table.snapshot(1).content_hash == first.content_hash


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-041")
def test_an_earlier_read_is_unchanged_by_a_later_commit(stack_catalog: object) -> None:
    """Point-in-time safety is why the plane exists, so it is checked wherever
    the plane is asked to live."""
    table = IcebergTable(
        name=f"cex_trades_{uuid.uuid4().hex[:8]}",
        schema=_schema(),
        catalog=stack_catalog,  # type: ignore[arg-type]
    )
    table.append([_row(1), _row(2)])
    before = table.read(snapshot_id=1).num_rows

    table.append([_row(3)])

    assert table.read(snapshot_id=1).num_rows == before


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-041")
def test_the_same_factory_opens_both_catalogs() -> None:
    """[[ADR-060]]'s actual claim, which no behavioural test can make.

    A catalog that worked on PostgreSQL through a second function would pass
    every other test in this file and be the second production path
    [[ADR-002]] refused. So the source is read: one factory, and nothing in it
    branching on the scheme.
    """
    from channelflow.lakehouse import iceberg

    source = Path(iceberg.__file__).read_text()
    factory = source[source.index("def catalog(") : source.index("def _as_location(")]

    for scheme in ("sqlite", "postgres", "postgresql"):
        assert scheme not in factory, f"the factory branches on {scheme}"
