"""The object store, behind a port.

# @trace: REQ-STORE-001

PRD section 29.0: "Any backend-specific DDL must live behind migrations/adapters
and must not leak into signal/channel domain code." This module is that
boundary, and it is deliberately tiny -- four operations, no query language, no
transactions.

`put_if_absent` is the only interesting one. It is the single primitive the
whole table layer's atomicity rests on: a commit succeeds by writing a manifest
that did not exist a moment ago, and fails by discovering that it did. A store
that cannot make that promise cannot host a table here, which is why the port
asks for it explicitly rather than leaving callers to emulate it with a read
followed by a write -- two operations that look correct and lose races.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol


class KeyExists(RuntimeError):
    """A conditional write found the key already there."""


class KeyMissing(LookupError):
    """A read named a key the store does not hold."""


class ConditionalWritesUnsupported(RuntimeError):
    """The backend cannot promise `put_if_absent`.

    Raised rather than falling back to read-then-write. A fallback would make
    every commit look atomic and lose the races it exists to catch -- and it
    would lose them silently, which is the worst property a storage layer can
    have.
    """


class ObjectStore(Protocol):
    """What the table layer needs from durable storage, and nothing more."""

    def put(self, key: str, body: bytes) -> None:
        """Write, overwriting whatever was there."""
        ...

    def put_if_absent(self, key: str, body: bytes) -> None:
        """Write only if the key does not exist; raise `KeyExists` if it does."""
        ...

    def get(self, key: str) -> bytes:
        """Read, or raise `KeyMissing`."""
        ...

    def list(self, prefix: str) -> list[str]:
        """Every key under `prefix`, sorted."""
        ...


class InMemoryObjectStore:
    """A store that keeps everything in a dict.

    For tests, and stated as such. [[ADR-002]] warns against developing against
    a filesystem and switching to S3 later, because that reintroduces exactly
    the local-versus-production divergence Principle VII exists to prevent. A
    test double behind the port is a different thing from a second production
    path: nothing here is reachable from a running system, and the S3
    implementation is the only one the table layer is ever configured with
    outside a test.
    """

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put(self, key: str, body: bytes) -> None:
        self._objects[key] = body

    def put_if_absent(self, key: str, body: bytes) -> None:
        if key in self._objects:
            raise KeyExists(key)
        self._objects[key] = body

    def get(self, key: str) -> bytes:
        try:
            return self._objects[key]
        except KeyError as exc:
            raise KeyMissing(key) from exc

    def list(self, prefix: str) -> list[str]:
        return sorted(key for key in self._objects if key.startswith(prefix))

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._objects))


class S3ObjectStore:
    """The production store: S3-compatible object storage.

    [[ADR-002]] makes this the canonical durable data plane. `put_if_absent`
    uses S3's `If-None-Match: *` precondition, which is one round trip and
    genuinely atomic; a store whose backend does not support it raises
    `ConditionalWritesUnsupported` at the moment of the write rather than
    pretending.
    """

    def __init__(self, client: object, bucket: str, *, prefix: str = "") -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.rstrip("/") + "/" if prefix else ""

    def _key(self, key: str) -> str:
        return f"{self._prefix}{key}"

    def put(self, key: str, body: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=self._key(key), Body=body)  # type: ignore[attr-defined]

    def put_if_absent(self, key: str, body: bytes) -> None:
        try:
            self._client.put_object(  # type: ignore[attr-defined]
                Bucket=self._bucket, Key=self._key(key), Body=body, IfNoneMatch="*"
            )
        except Exception as exc:  # noqa: BLE001 -- botocore's errors are dynamic
            code = _error_code(exc)
            if code in ("PreconditionFailed", "ConditionalRequestConflict"):
                raise KeyExists(key) from exc
            if code in ("NotImplemented", "InvalidRequest", "MethodNotAllowed"):
                raise ConditionalWritesUnsupported(
                    f"the backend refused a conditional write ({code}); a table cannot "
                    "commit atomically against it, and emulating the guarantee with a "
                    "read followed by a write would lose races silently"
                ) from exc
            raise

    def get(self, key: str) -> bytes:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=self._key(key))  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001 -- botocore's errors are dynamic
            if _error_code(exc) in ("NoSuchKey", "404"):
                raise KeyMissing(key) from exc
            raise
        body: bytes = response["Body"].read()
        return body

    def list(self, prefix: str) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")  # type: ignore[attr-defined]
        found: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._key(prefix)):
            for item in page.get("Contents", ()):
                found.append(str(item["Key"])[len(self._prefix) :])
        return sorted(found)


def _error_code(exc: Exception) -> str:
    """botocore's error code, or an empty string.

    Read defensively: `ClientError.response` is a plain dict and a transport
    error has none at all, so a missing key here must not turn one failure into
    a different, more confusing one.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return ""
    error = response.get("Error")
    if not isinstance(error, dict):
        return ""
    return str(error.get("Code", ""))
