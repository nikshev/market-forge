"""How the read API starts.

# @trace: REQ-WP-064

PRD §6.2's MVP deployment names an `api` service. There was no way to run one:
`create_app` takes an already-built repository, `LakehouseRepository` takes a
`Catalog`, and the only place a catalog was opened was a test fixture pointing
at a temporary directory. **An image was not the first missing piece; a way to
start was.**

`lakehouse.catalog` already takes a PostgreSQL URI and an S3 warehouse and
deliberately does not branch on the scheme ([[REQ-WP-041]]), so this is only the
part that reads the environment and calls it.

**Nothing here defaults.** PRD §34 keeps credentials in the environment, and a
composition root that fell back to a local directory when the warehouse was
unset would start in production and serve an empty one -- which reads as a quiet
market, not as a misconfiguration. A missing variable refuses to start and names
itself.
"""

from __future__ import annotations

from fastapi import FastAPI

from channelflow.api.app import create_app
from channelflow.api.lakehouse_repository import LakehouseRepository
from channelflow.api.readiness import catalog_probe
from channelflow.lakehouse import catalog as open_catalog
from channelflow.lakehouse.iceberg import NAMESPACE
from channelflow.settings import (
    CATALOG_URI,
    REQUIRED,
    WAREHOUSE,
    MissingConfiguration,
    Settings,
    settings_from_env,
)


def build_app(settings: Settings) -> FastAPI:
    """The composition root: configuration in, application out."""
    store = open_catalog(
        uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
    )
    return create_app(
        repository=LakehouseRepository(catalog=store),
        readiness=catalog_probe(lambda: store.list_tables(NAMESPACE)),
    )


def application() -> FastAPI:
    """The entry point a server imports.

    A factory rather than a module-level object, so importing this module does
    not require the environment -- a test that checks the refusal above has to
    be able to import the thing that refuses.
    """
    return build_app(settings_from_env())


__all__ = [
    "CATALOG_URI",
    "REQUIRED",
    "WAREHOUSE",
    "MissingConfiguration",
    "Settings",
    "application",
    "build_app",
    "settings_from_env",
]
