"""Fixtures every suite can reach (REQ-WP-039).

The canonical plane is Apache Iceberg ([[ADR-060]]), and a table is found
through a catalog rather than handed a store. This gives every test one --
SQLite in a temporary directory, which is the same catalog implementation the
stack runs against PostgreSQL with a different URL, and which keeps the fast
gate free of services (REQ-INFRA-002).

Function-scoped on purpose: these write real files, and a shared warehouse would
let one test read another's snapshots and pass for the wrong reason.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog


@pytest.fixture
def catalog(tmp_path: Path) -> Catalog:
    return open_catalog(uri=f"sqlite:///{tmp_path}/catalog.db", warehouse=str(tmp_path))
