"""The backup round trip against a real object store (REQ-WP-037).

The unit tests run against a double behind the port. This one runs against
MinIO, because a backup is the one feature whose failure is only discovered when
it is needed, and CLAUDE.md's rule is that "CI is where `implemented` is
earned".

What a double cannot prove here: that `put_if_absent` skips an already-copied
object on the real backend rather than raising something else, that a listing
over two prefixes pages the way the walk assumes, and that the bytes a restore
reads back are the bytes it wrote. All three are load-bearing, and all three are
backend behaviour.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from channelflow.lakehouse import (
    Column,
    S3ObjectStore,
    Schema,
    Table,
    TargetNotEmpty,
    back_up,
    restore,
    verify,
)

SECOND = 1_000_000_000


def _env() -> dict[str, str]:
    """The stack's settings, from `.env` or `.env.example`.

    Same reader as the other integration tests: a fresh checkout has no `.env`
    yet, and the failure should be "the stack is not running" rather than "no
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


def _client() -> object:
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
    return client


@pytest.fixture
def stores() -> tuple[S3ObjectStore, S3ObjectStore, S3ObjectStore]:
    """Three prefixes in one bucket: the live plane, the backup, and where a
    restore lands.

    A fresh prefix per test, for the reason the other MinIO tests give: these
    write real objects, and a reused prefix would read another run's snapshots
    and pass for the wrong reason.
    """
    client = _client()
    env = _env()
    run = uuid.uuid4()
    return tuple(  # type: ignore[return-value]
        S3ObjectStore(client, env["MINIO_BUCKET"], prefix=f"backup-test/{run}/{role}")
        for role in ("source", "backup", "home")
    )


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
def test_a_table_survives_a_round_trip_through_a_real_object_store(
    stores: tuple[S3ObjectStore, S3ObjectStore, S3ObjectStore],
) -> None:
    """The claim the whole requirement is about, made against the real thing."""
    source, backup, home = stores
    table = Table(name="cex_trades", schema=_schema(), store=source)
    table.append([_row(1), _row(2)])
    table.append([_row(3)])

    copied = back_up("cex_trades", source=source, target=backup)
    landed = restore("cex_trades", source=backup, target=home)

    assert copied.snapshots == (1, 2)
    assert landed.landed_on == 2

    restored = Table(name="cex_trades", schema=_schema(), store=home)
    assert restored.read().to_pylist() == table.read().to_pylist()
    # Point-in-time reads survive too, which is what the history is for.
    assert restored.read(snapshot_id=1).num_rows == 2
    assert restored.read(as_of_ns=2 * SECOND).num_rows == 2


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-037")
def test_the_copy_verifies_against_the_source_s_identity(
    stores: tuple[S3ObjectStore, S3ObjectStore, S3ObjectStore],
) -> None:
    """Byte digests and the content hash, both computed over what the backend
    actually stored and returned."""
    source, backup, _ = stores
    table = Table(name="cex_trades", schema=_schema(), store=source)
    table.append([_row(1)])
    table.append([_row(2)])
    current = table.current()
    assert current is not None

    back_up("cex_trades", source=source, target=backup)

    report = verify("cex_trades", store=backup, expect_content_hash=current.content_hash)
    assert report.ok, (report.missing, report.corrupt, report.identity_ok)


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-037")
def test_re_running_a_backup_copies_nothing_and_raises_nothing(
    stores: tuple[S3ObjectStore, S3ObjectStore, S3ObjectStore],
) -> None:
    """`put_if_absent` on the real backend, which is the only place its
    behaviour is a guarantee rather than a mapping.

    A second run writing zero objects is also what makes an interrupted backup
    resumable rather than a fresh copy.
    """
    source, backup, _ = stores
    table = Table(name="cex_trades", schema=_schema(), store=source)
    table.append([_row(1)])

    first = back_up("cex_trades", source=source, target=backup)
    again = back_up("cex_trades", source=source, target=backup)

    assert first.objects > 0
    assert again.objects == 0


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-037")
def test_restoring_over_a_live_table_is_refused_on_the_real_backend(
    stores: tuple[S3ObjectStore, S3ObjectStore, S3ObjectStore],
) -> None:
    """The listing that detects a non-empty target is a real listing here."""
    source, backup, home = stores
    Table(name="cex_trades", schema=_schema(), store=source).append([_row(1)])
    Table(name="cex_trades", schema=_schema(), store=home).append([_row(9)])
    back_up("cex_trades", source=source, target=backup)

    with pytest.raises(TargetNotEmpty):
        restore("cex_trades", source=backup, target=home)
