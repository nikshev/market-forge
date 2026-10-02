"""An in-memory S3 client with exactly the calls the archive tooling makes (REQ-WP-078).

# @trace: REQ-WP-078

`moto` is not a dependency of this project, and adding it for one tool would be a
supply-chain cost for a dictionary. This is the repository's habit: `ReplayTransport`
stands in for the socket and `FakeClock` for the clock, and neither is a mock -- they
are the other implementation of the seam.

What it models, because the migration's safety rests on it:

* **ETags derive from content**, as S3's do for a single-part object, so a copy has
  the source's ETag and a corrupted copy does not. That is what lets "verify before
  delete" be a comparison and not a hope.
* **Calls are recorded**, so a dry-run can be shown to have changed nothing.
* **Two faults can be switched on**: a copy that comes out wrong, and a delete that
  raises -- the two ways an interrupted migration goes bad.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


class NoSuchKey(Exception):  # noqa: N818 -- S3's own name
    """What `get_object` and `head_object` raise for an absent key."""


@dataclass
class FakeS3:
    objects: dict[tuple[str, str], bytes] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)
    #: Make every `copy_object` write bytes that differ from the source's.
    corrupt_copies: bool = False
    #: Make every `delete_object` raise, as a process killed between copy and delete would.
    fail_deletes: bool = False
    page_size: int = 1000

    # -- writes ---------------------------------------------------------------

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **_: Any) -> dict[str, Any]:
        self.calls.append(("put", Key))
        self.objects[(Bucket, Key)] = bytes(Body)
        return {"ETag": _etag(Body)}

    def copy_object(
        self, *, Bucket: str, Key: str, CopySource: dict[str, str], **_: Any
    ) -> dict[str, Any]:
        self.calls.append(("copy", Key))
        body = self._get(CopySource["Bucket"], CopySource["Key"])
        if self.corrupt_copies:
            body = body[:-1] + bytes([(body[-1] + 1) % 256]) if body else b"\x00"
        self.objects[(Bucket, Key)] = body
        return {"CopyObjectResult": {"ETag": _etag(body)}}

    def delete_object(self, *, Bucket: str, Key: str, **_: Any) -> dict[str, Any]:
        self.calls.append(("delete", Key))
        if self.fail_deletes:
            raise RuntimeError("the connection dropped between copy and delete")
        self.objects.pop((Bucket, Key), None)
        return {}

    # -- reads ----------------------------------------------------------------

    def get_object(self, *, Bucket: str, Key: str, **_: Any) -> dict[str, Any]:
        self.calls.append(("get", Key))
        body = self._get(Bucket, Key)
        return {"Body": _Body(body), "ContentLength": len(body), "ETag": _etag(body)}

    def head_object(self, *, Bucket: str, Key: str, **_: Any) -> dict[str, Any]:
        self.calls.append(("head", Key))
        body = self._get(Bucket, Key)
        return {"ContentLength": len(body), "ETag": _etag(body)}

    def list_objects_v2(
        self,
        *,
        Bucket: str,
        Prefix: str = "",
        ContinuationToken: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        self.calls.append(("list", Prefix))
        keys = sorted(k for (b, k) in self.objects if b == Bucket and k.startswith(Prefix))
        start = int(ContinuationToken) if ContinuationToken else 0
        page = keys[start : start + self.page_size]
        result: dict[str, Any] = {
            "Contents": [{"Key": k, "Size": len(self.objects[(Bucket, k)])} for k in page],
            "IsTruncated": start + self.page_size < len(keys),
        }
        if result["IsTruncated"]:
            result["NextContinuationToken"] = str(start + self.page_size)
        return result

    # -- helpers for tests ----------------------------------------------------

    def keys(self, bucket: str) -> list[str]:
        return sorted(k for (b, k) in self.objects if b == bucket)

    def snapshot(self) -> dict[tuple[str, str], bytes]:
        return dict(self.objects)

    def _get(self, bucket: str, key: str) -> bytes:
        try:
            return self.objects[(bucket, key)]
        except KeyError:
            raise NoSuchKey(key) from None


class _Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data


def _etag(body: bytes) -> str:
    return '"' + hashlib.md5(body, usedforsecurity=False).hexdigest() + '"'
