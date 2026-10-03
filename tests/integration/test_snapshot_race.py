"""A reader beside a writer, against the stack's own catalog and bucket (REQ-WP-079).

**Evidence, not proof.** This can pass by luck on unfixed code: it needs a commit to land in the
few milliseconds between two loads, and nothing here makes it. Measured when it was written, on the
old code: one reader for five seconds passed 3 runs of 3 (no evidence at all); four readers for
eight seconds failed 3 of 3 with the production message, and pass on the fix 2 of 2. The proof is
`tests/unit/lakehouse/test_single_load.py`, where a catalog commits between *every* two loads. What
this adds is the real thing the fault was found on -- PostgreSQL holding the pointer, MinIO holding
the files, two threads, no wrapper -- so a fix that held in a unit test and failed on the real
catalog would show here.
"""

from __future__ import annotations

import threading
import time

import pytest

from channelflow.lakehouse import IcebergTable
from channelflow.lakehouse.iceberg import NoSuchSnapshot

from .test_catalog_on_postgres import _row, _schema, stack_catalog, table_name  # noqa: F401

DURATION_SECONDS = 8.0
READERS = 4


@pytest.mark.integration
@pytest.mark.trace("REQ-WP-079")
def test_a_reader_beside_a_writer_never_meets_a_snapshot_that_is_not_there(
    stack_catalog: object,  # noqa: F811
    table_name: str,  # noqa: F811
) -> None:
    writer = IcebergTable(name=table_name, schema=_schema(), catalog=stack_catalog)  # type: ignore[arg-type]
    writer.append([_row(0)])

    stop = threading.Event()
    failures: list[BaseException] = []
    commits = 0
    reads = 0
    lock = threading.Lock()

    def write() -> None:
        nonlocal commits
        index = 1
        try:
            while not stop.is_set():
                writer.append([_row(index)])
                index += 1
                commits += 1
        except BaseException as error:  # noqa: BLE001 -- anything is a failure of the run
            failures.append(error)

    def read_loop() -> None:
        nonlocal reads
        handle = IcebergTable(name=table_name, schema=_schema(), catalog=stack_catalog)  # type: ignore[arg-type]
        while not stop.is_set() and not failures:
            try:
                handle.read()
                handle.current()
            except NoSuchSnapshot as error:
                failures.append(error)
            except BaseException as error:  # noqa: BLE001
                failures.append(error)
            with lock:
                reads += 1

    threads = [threading.Thread(target=write, name="writer")]
    threads += [threading.Thread(target=read_loop, name=f"reader-{i}") for i in range(READERS)]
    for thread in threads:
        thread.start()
    time.sleep(DURATION_SECONDS)
    stop.set()
    for thread in threads:
        thread.join(timeout=60)

    assert not failures, f"after {reads} reads and {commits} commits: {failures[0]!r}"
    assert commits >= 2, "the writer never committed, so nothing was raced"
