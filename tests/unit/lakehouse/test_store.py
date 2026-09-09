"""The object-store port, and the one guarantee the table layer rests on.

REQ-STORE-001, PRD §29.0.
"""

from __future__ import annotations

from typing import Any

import pytest

from channelflow.lakehouse import (
    ConditionalWritesUnsupported,
    InMemoryObjectStore,
    KeyExists,
    KeyMissing,
    S3ObjectStore,
)


class FakeClientError(Exception):
    """Shaped like botocore's `ClientError`, without the dependency on its
    exception hierarchy: the store reads `.response["Error"]["Code"]` and
    nothing else, so that is all a double has to have."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    """The four calls `S3ObjectStore` makes, and a way to fail any of them."""

    def __init__(self, *, put_error: str | None = None, get_error: str | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_error = put_error
        self.get_error = get_error
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)
        if self.put_error:
            raise FakeClientError(self.put_error)
        self.objects[kwargs["Key"]] = kwargs["Body"]

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        if self.get_error:
            raise FakeClientError(self.get_error)

        class _Body:
            def __init__(self, payload: bytes) -> None:
                self._payload = payload

            def read(self) -> bytes:
                return self._payload

        return {"Body": _Body(self.objects[kwargs["Key"]])}

    def get_paginator(self, _name: str) -> Any:
        objects = self.objects

        class _Paginator:
            def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
                prefix = kwargs["Prefix"]
                return [
                    {
                        "Contents": [
                            {"Key": key} for key in sorted(objects) if key.startswith(prefix)
                        ]
                    }
                ]

        return _Paginator()


@pytest.mark.trace("REQ-STORE-001")
def test_a_conditional_write_refuses_a_key_that_is_already_there() -> None:
    """The single primitive the table layer's atomicity rests on."""
    store = InMemoryObjectStore()
    store.put_if_absent("k", b"first")

    with pytest.raises(KeyExists, match="k"):
        store.put_if_absent("k", b"second")
    assert store.get("k") == b"first"


@pytest.mark.trace("REQ-STORE-001")
def test_an_unconditional_write_overwrites() -> None:
    """Data files are written this way on purpose: a rewrite of a data file is a
    rewrite of bytes nothing references yet."""
    store = InMemoryObjectStore()
    store.put("k", b"first")
    store.put("k", b"second")

    assert store.get("k") == b"second"


@pytest.mark.trace("REQ-STORE-001")
def test_a_missing_key_is_a_refusal_rather_than_an_empty_read() -> None:
    """Empty bytes are a valid object. A store that returned them for a key it
    does not hold would make a missing manifest look like an empty one."""
    with pytest.raises(KeyMissing, match="nope"):
        InMemoryObjectStore().get("nope")


@pytest.mark.trace("REQ-STORE-001")
def test_listing_is_by_prefix_and_sorted() -> None:
    """Sorted because the table layer reads the highest manifest version off the
    end of this list, and a store that returned its keys in insertion order
    would put the newest snapshot wherever it happened to land."""
    store = InMemoryObjectStore()
    for key in ("t/metadata/v2.json", "t/metadata/v1.json", "other/x"):
        store.put(key, b"")

    assert store.list("t/metadata/") == ["t/metadata/v1.json", "t/metadata/v2.json"]
    assert store.list("") == ["other/x", "t/metadata/v1.json", "t/metadata/v2.json"]


@pytest.mark.trace("REQ-STORE-001")
def test_the_s3_store_asks_for_a_precondition_on_a_conditional_write() -> None:
    """`If-None-Match: *` is one round trip and genuinely atomic. Emulating it
    with a read followed by a write is two operations that look correct and lose
    races."""
    client = FakeS3()
    S3ObjectStore(client, "bucket").put_if_absent("k", b"body")

    assert client.calls[-1]["IfNoneMatch"] == "*"


@pytest.mark.trace("REQ-STORE-001")
def test_an_unconditional_write_asks_for_no_precondition() -> None:
    client = FakeS3()
    S3ObjectStore(client, "bucket").put("k", b"body")

    assert "IfNoneMatch" not in client.calls[-1]


@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.parametrize("code", ["PreconditionFailed", "ConditionalRequestConflict"])
def test_the_s3_store_reports_a_lost_race_as_a_lost_race(code: str) -> None:
    """Both codes mean the same thing to a caller: someone else got there
    first."""
    store = S3ObjectStore(FakeS3(put_error=code), "bucket")

    with pytest.raises(KeyExists):
        store.put_if_absent("k", b"body")


@pytest.mark.trace("REQ-STORE-001")
@pytest.mark.parametrize("code", ["NotImplemented", "InvalidRequest", "MethodNotAllowed"])
def test_a_backend_that_cannot_do_conditional_writes_is_refused(code: str) -> None:
    """Rather than silently emulated.

    A fallback would make every commit look atomic and lose the races it exists
    to catch -- silently, which is the worst property a storage layer can have.
    """
    store = S3ObjectStore(FakeS3(put_error=code), "bucket")

    with pytest.raises(ConditionalWritesUnsupported, match="lose races silently"):
        store.put_if_absent("k", b"body")


@pytest.mark.trace("REQ-STORE-001")
def test_an_unrecognised_failure_is_not_swallowed() -> None:
    """A credentials error is not a lost race and must not read as one."""
    store = S3ObjectStore(FakeS3(put_error="AccessDenied"), "bucket")

    with pytest.raises(FakeClientError):
        store.put_if_absent("k", b"body")


@pytest.mark.trace("REQ-STORE-001")
def test_the_s3_store_reports_a_missing_object_as_missing() -> None:
    store = S3ObjectStore(FakeS3(get_error="NoSuchKey"), "bucket")

    with pytest.raises(KeyMissing):
        store.get("k")


@pytest.mark.trace("REQ-STORE-001")
def test_a_transport_failure_with_no_error_code_is_not_mistaken_for_one() -> None:
    """`_error_code` reads defensively: a transport error has no `response` at
    all, and a missing key there must not turn one failure into a different,
    more confusing one."""

    class Rude:
        def put_object(self, **_: Any) -> None:
            raise RuntimeError("connection reset")

    with pytest.raises(RuntimeError, match="connection reset"):
        S3ObjectStore(Rude(), "bucket").put_if_absent("k", b"body")


@pytest.mark.trace("REQ-STORE-001")
def test_the_prefix_is_added_on_the_way_in_and_taken_off_on_the_way_out() -> None:
    """A table's keys are its own; where the bucket puts them is the store's
    business. A listing that leaked the prefix would make every key in a manifest
    unresolvable from a differently-prefixed store."""
    client = FakeS3()
    store = S3ObjectStore(client, "bucket", prefix="channelflow/")
    store.put("t/metadata/v1.json", b"body")

    assert client.calls[-1]["Key"] == "channelflow/t/metadata/v1.json"
    assert store.list("t/") == ["t/metadata/v1.json"]
    assert store.get("t/metadata/v1.json") == b"body"
