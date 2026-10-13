"""Every table the system writes is compacted (REQ-WP-104).

`TABLES` in the maintenance entrypoint is named rather than discovered, so that compacting
something is a decision somebody made. The cost of that is a table nobody decided about: on
2026-10-13 `volume_bins` -- written by every ingest daemon -- was not in the list, had 5,077 files,
and its read took 23 s, which is the volume profile pane taking 40-80 s to appear.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import channelflow.tables as tables_package
from channelflow.lakehouse import Catalog
from channelflow.pipeline.maintenance_main import TABLES

pytestmark = pytest.mark.trace("REQ-WP-104")


def declared_table_names() -> set[str]:
    names: set[str] = set()
    for module_info in pkgutil.iter_modules(tables_package.__path__):
        module = importlib.import_module(f"channelflow.tables.{module_info.name}")
        for attribute, value in vars(module).items():
            if attribute.endswith("TABLE_NAME") and isinstance(value, str):
                names.add(value)
    return names


def test_the_walk_finds_the_tables_it_should() -> None:
    names = declared_table_names()

    assert {"bars", "feature_snapshots", "volume_bins", "consensus"} <= names
    assert len(names) >= 20, "the walk found too few table names to mean anything"


def test_maintenance_names_a_factory_for_every_table_a_module_declares(catalog: Catalog) -> None:
    compacted = {factory(catalog).name for factory in TABLES.values()}

    assert declared_table_names() - compacted == set()
