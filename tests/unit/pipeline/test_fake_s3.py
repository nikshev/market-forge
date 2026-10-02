"""The fake the migration is tested against has to behave like what it stands for (REQ-WP-078).

# @trace: REQ-WP-078

A migration proven safe against a fake that is lenient proves nothing, so the fake
is tested for the three properties the proof leans on.
"""

from __future__ import annotations

import pytest

from .fake_s3 import FakeS3, NoSuchKey

B = "bucket"


@pytest.mark.trace("REQ-WP-078")
def test_a_copy_has_the_sources_size_and_etag() -> None:
    s3 = FakeS3()
    s3.put_object(Bucket=B, Key="a", Body=b"frames")
    s3.copy_object(Bucket=B, Key="b", CopySource={"Bucket": B, "Key": "a"})

    assert s3.head_object(Bucket=B, Key="a") == s3.head_object(Bucket=B, Key="b")


@pytest.mark.trace("REQ-WP-078")
def test_a_corrupted_copy_does_not_match_the_source() -> None:
    s3 = FakeS3(corrupt_copies=True)
    s3.put_object(Bucket=B, Key="a", Body=b"frames")
    s3.copy_object(Bucket=B, Key="b", CopySource={"Bucket": B, "Key": "a"})

    assert s3.head_object(Bucket=B, Key="a")["ETag"] != s3.head_object(Bucket=B, Key="b")["ETag"]


@pytest.mark.trace("REQ-WP-078")
def test_listing_pages_and_a_missing_key_raises() -> None:
    s3 = FakeS3(page_size=2)
    for name in "abcde":
        s3.put_object(Bucket=B, Key=name, Body=b"x")

    seen: list[str] = []
    token: str | None = None
    while True:
        page = s3.list_objects_v2(Bucket=B, **({"ContinuationToken": token} if token else {}))
        seen += [o["Key"] for o in page["Contents"]]
        token = page.get("NextContinuationToken")
        if not token:
            break

    assert seen == list("abcde")
    with pytest.raises(NoSuchKey):
        s3.head_object(Bucket=B, Key="absent")


@pytest.mark.trace("REQ-WP-078")
def test_a_delete_can_be_made_to_fail_and_leaves_the_object() -> None:
    s3 = FakeS3(fail_deletes=True)
    s3.put_object(Bucket=B, Key="a", Body=b"x")

    with pytest.raises(RuntimeError):
        s3.delete_object(Bucket=B, Key="a")
    assert s3.keys(B) == ["a"]
