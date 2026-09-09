"""The canonical plane against a real object store (REQ-STORE-001).

The unit tests run against a double behind the port. These run against MinIO,
because two things about `S3ObjectStore` cannot be tested any other way and both
are load-bearing:

- whether `If-None-Match: *` actually works on the backend the stack provides.
  A double that raises the error code it was told to raise proves the mapping,
  not the guarantee -- and the whole table layer's atomicity is that guarantee.
- whether a real listing pages, prefixes and sorts the way the table layer's
  version discovery assumes.

[[ADR-002]] made S3-compatible object storage the canonical data plane precisely
so that local and production would not diverge. That is only true if something
checks the real thing, which is what CLAUDE.md means by "CI is where
`implemented` is earned".
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from channelflow.lakehouse import (
    Column,
    KeyExists,
    S3ObjectStore,
    Schema,
    Table,
    query,
)

SECOND = 1_000_000_000


def _env() -> dict[str, str]:
    """The stack's settings, from `.env` or `.env.example`.

    Same reader as `test_dev_stack.py`: a fresh checkout has no `.env` yet, and
    the failure should be "the stack is not running" rather than "no
    configuration".
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
def store() -> S3ObjectStore:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError

    env = _env()
    client = boto3.client(
        "s3",
        endpoint_url=f"http://127.0.0.1:{env['MINIO_PORT']}",
        aws_access_key_id=env["MINIO_ROOT_USER"],
        aws_secret_access_key=env["MINIO_ROOT_PASSWORD"],
        config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 1}),
    )
    try:
        client.list_buckets()
    except (BotoCoreError, ClientError, OSError) as exc:
        pytest.fail(
            f"Object store is not answering on port {env['MINIO_PORT']}: {exc}. Run `make up`."
        )
    # A fresh prefix per test: these write real objects, and a test that reused
    # a prefix would read another run's snapshots and pass for the wrong reason.
    return S3ObjectStore(client, env["MINIO_BUCKET"], prefix=f"lakehouse-test/{uuid.uuid4()}")


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
def test_a_table_commits_reads_and_time_travels_on_a_real_object_store(
    store: S3ObjectStore,
) -> None:
    """The whole round trip, against the store [[ADR-002]] chose."""
    table = Table(name="cex_trades", schema=_schema(), store=store)

    first = table.append([_row(1), _row(2)])
    second = table.append([_row(3)])

    assert table.snapshot_ids() == (1, 2)
    assert table.read(snapshot_id=1).num_rows == 2
    assert table.read().num_rows == 3
    assert table.read(as_of_ns=2 * SECOND).num_rows == 2
    assert table.snapshot(1).content_hash == first.content_hash
    assert second.parent_id == 1


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
def test_the_backend_really_refuses_a_second_write_to_the_same_key(
    store: S3ObjectStore,
) -> None:
    """The guarantee, not the mapping.

    A unit test proves that a `PreconditionFailed` becomes a `KeyExists`. Only
    this one proves the backend sends a `PreconditionFailed` at all -- and if it
    does not, every commit in the table layer is a race nobody loses and nobody
    notices.
    """
    store.put_if_absent("probe.json", b"first")

    with pytest.raises(KeyExists):
        store.put_if_absent("probe.json", b"second")
    assert store.get("probe.json") == b"first"


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
def test_a_listing_from_a_real_store_orders_manifest_versions(
    store: S3ObjectStore,
) -> None:
    """The table layer takes the newest snapshot off the end of this list.

    Zero-padded versions make a lexical listing a numeric ordering, which is the
    assumption that would break silently at the tenth commit if the padding were
    dropped.
    """
    table = Table(name="cex_trades", schema=_schema(), store=store)
    for index in range(1, 12):
        table.append([_row(index)])

    assert table.snapshot_ids() == tuple(range(1, 12))
    current = table.current()
    assert current is not None and current.snapshot_id == 11


@pytest.mark.integration
@pytest.mark.trace("REQ-STORE-001")
def test_duckdb_queries_an_extract_from_a_real_store(store: S3ObjectStore) -> None:
    """PRD §29.0's "bounded extracts with DuckDB", over objects that really came
    off the network."""
    table = Table(name="cex_trades", schema=_schema(), store=store)
    table.append([_row(1), _row(2)])
    table.append([_row(3)])

    rows = query(table, 'SELECT count(*) AS n FROM "cex_trades"')

    assert rows.to_pylist() == [{"n": 3}]
