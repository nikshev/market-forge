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


def _get(url: str) -> tuple[int, str, str]:
    """Status, content type and body, or a failure naming the stack."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return (
                response.status,
                response.headers.get("content-type", ""),
                response.read().decode(),
            )
    except OSError as exc:
        pytest.fail(f"{url} did not answer: {exc}. Run `docker compose up -d --build`.")


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-075")
def test_the_markets_route_reaches_the_bundle() -> None:
    """`/markets` is served the application, not a 404 (REQ-WP-075).

    The view itself is exercised by the web suite; what only the deployment can
    show is that the route is *reachable* -- nginx falls back to `index.html`,
    and a static server that 404s `/markets` would make the feature unreachable
    however correct the bundle is.
    """
    env = _env()
    base = f"http://127.0.0.1:{env['WEB_PORT']}"

    for path in ("/", "/markets"):
        status, content_type, body = _get(f"{base}{path}")
        assert status == 200, f"{path} answered {status}"
        assert "text/html" in content_type, f"{path} answered {content_type!r}"
        assert '<div id="root">' in body, f"{path} did not serve the application shell"


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-075")
def test_the_markets_read_has_the_shape_the_view_consumes() -> None:
    """§28.1's read, as the markets view reads it (REQ-WP-075).

    The rows' field names are the contract between the bundle and the API. The
    list may legitimately be empty -- this deployment's is -- and an empty list
    is asserted as a valid answer rather than treated as a failure.
    """
    import json

    env = _env()
    status, content_type, body = _get(f"http://127.0.0.1:{env['API_PORT']}/api/v1/markets")

    assert status == 200
    assert "application/json" in content_type
    markets = json.loads(body)["markets"]
    for row in markets:
        assert {"venue", "symbol", "market_type", "setup_score", "rank_score", "confidence"} <= set(
            row
        )
        for field in ("setup_score", "rank_score", "confidence"):
            assert row[field] is None or isinstance(row[field], (int, float)), (field, row[field])
