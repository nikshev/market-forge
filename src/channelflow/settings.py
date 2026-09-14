"""Where this system's data is, read from the environment.

# @trace: REQ-WP-064
# @trace: REQ-WP-066

Shared by every process that reaches the canonical plane -- the read API and the
ingest daemon -- because they reach the same plane and a second reader of the
same variables would drift from the first.

**Nothing here defaults.** PRD §34 keeps credentials in the environment, and the
convenient default is a local directory: a process serving or filling an empty
warehouse looks exactly like a market where nothing happened.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

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
