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

import os
from collections.abc import Mapping
from dataclasses import dataclass

from fastapi import FastAPI

from channelflow.api.app import create_app
from channelflow.api.lakehouse_repository import LakehouseRepository
from channelflow.api.readiness import catalog_probe
from channelflow.lakehouse import catalog as open_catalog
from channelflow.lakehouse.iceberg import NAMESPACE

#: Where the Iceberg catalog lives, and where its data does. Both required:
#: either one alone describes half a lakehouse.
CATALOG_URI = "CHANNELFLOW_CATALOG_URI"
WAREHOUSE = "CHANNELFLOW_WAREHOUSE"

REQUIRED = (CATALOG_URI, WAREHOUSE)

#: Storage options, by the name pyiceberg knows them. Read from the environment
#: under the names the object store already uses in this repository, so a
#: deployment has one set of credentials rather than two spellings of one.
_STORAGE = {
    "CHANNELFLOW_S3_ENDPOINT": "s3.endpoint",
    "CHANNELFLOW_S3_ACCESS_KEY_ID": "s3.access-key-id",
    "CHANNELFLOW_S3_SECRET_ACCESS_KEY": "s3.secret-access-key",
    "CHANNELFLOW_S3_REGION": "s3.region",
}


class MissingConfiguration(RuntimeError):
    """A required variable is unset.

    Raised rather than defaulted: the default that would be convenient here is a
    local directory, and a process serving an empty warehouse looks exactly like
    a market where nothing happened.
    """


@dataclass(frozen=True)
class Settings:
    """Everything the API needs to reach its data."""

    catalog_uri: str
    warehouse: str
    storage: Mapping[str, str]


def settings_from_env(environ: Mapping[str, str] | None = None) -> Settings:
    """Read the configuration, refusing what is absent or blank.

    Blank counts as absent. An empty environment variable is what a shell gives
    for one nobody set, and a catalog URI of `""` would fail later and
    elsewhere -- in pyiceberg, about a URL, rather than here, about a
    deployment.
    """
    values = os.environ if environ is None else environ
    missing = [name for name in REQUIRED if not values.get(name, "").strip()]
    if missing:
        raise MissingConfiguration(
            f"{', '.join(missing)} must be set; there is no default, because the "
            "convenient one is a local directory and a process serving an empty "
            "warehouse is indistinguishable from a quiet market"
        )
    storage = {
        prop: values[name].strip()
        for name, prop in _STORAGE.items()
        if values.get(name, "").strip()
    }
    return Settings(
        catalog_uri=values[CATALOG_URI].strip(),
        warehouse=values[WAREHOUSE].strip(),
        storage=storage,
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
