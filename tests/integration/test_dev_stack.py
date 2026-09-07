"""Integration tests for the local development stack (REQ-WP-001).

These connect to real services. They are the spec's SC-002: the start command
reports success only after each service answers a real request, and a container
that has started is not a service that is ready.

They fail with a clear message when the stack is not running, rather than
erroring obscurely -- a developer who forgot `make up` should be told so.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest


def _env() -> dict[str, str]:
    """Read .env if present, falling back to .env.example's defaults.

    Falling back matters: a fresh checkout has no .env yet, and the test should
    still report "the stack is not running" rather than "no configuration".
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


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-001")
def test_postgres_answers_a_query() -> None:
    """PostgreSQL is reachable and serves queries, not merely accepting TCP."""
    import asyncpg

    env = _env()

    async def _query() -> int:
        conn = await asyncpg.connect(
            user=env["POSTGRES_USER"],
            password=env["POSTGRES_PASSWORD"],
            database=env["POSTGRES_DB"],
            host="127.0.0.1",
            port=int(env["POSTGRES_PORT"]),
            timeout=5,
        )
        try:
            return await conn.fetchval("SELECT 1")
        finally:
            await conn.close()

    try:
        result = asyncio.run(_query())
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.fail(
            f"PostgreSQL is not answering on port {env['POSTGRES_PORT']}: {exc}. Run `make up`."
        )
    assert result == 1


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-001")
def test_object_store_lists_buckets() -> None:
    """The object store answers the S3 API and the development bucket exists."""
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
        buckets = {b["Name"] for b in client.list_buckets()["Buckets"]}
    except (BotoCoreError, ClientError, OSError) as exc:
        pytest.fail(
            f"Object store is not answering on port {env['MINIO_PORT']}: {exc}. Run `make up`."
        )
    assert env["MINIO_BUCKET"] in buckets, (
        f"bucket {env['MINIO_BUCKET']!r} is missing; `make up` should create it."
        f" Found: {sorted(buckets)}"
    )
