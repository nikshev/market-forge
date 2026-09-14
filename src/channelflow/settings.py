"""Where this system's data is, read from the environment.

# @trace: REQ-WP-064
# @trace: REQ-WP-066
# @trace: REQ-WP-072

Shared by every process that reaches the canonical plane -- the read API and the
ingest daemon -- because they reach the same plane and a second reader of the
same variables would drift from the first.

**Nothing here defaults.** PRD §34 keeps credentials in the environment, and the
convenient default is a local directory: a process serving or filling an empty
warehouse looks exactly like a market where nothing happened.

**And nothing here renders a credential.** §34 also asks that secrets be redacted
from logs. Measured before that was true: `Settings` was a plain frozen
dataclass, so `repr` printed the Postgres password inside `catalog_uri` *and*
`storage['s3.secret-access-key']` in full -- and a log line, an f-string, an
assertion message or a traceback showing locals would each have delivered them.
The leak was in the type, so the mask is too.

What stays visible is as much a part of that rule as what goes. A mask that hid
everything would make the object useless to read, and whoever needed the host
would render the fields one at a time: the same leak by a longer road.
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


#: Where the public read API's limits come from (PRD §34, Principle X).
CORS_ORIGINS = "CHANNELFLOW_CORS_ORIGINS"
RATE_LIMIT = "CHANNELFLOW_RATE_LIMIT"
RATE_WINDOW_SECONDS = "CHANNELFLOW_RATE_WINDOW_SECONDS"

#: The window a limit gets when only the count is configured. One minute is the
#: unit rate limits are usually quoted in, and it is overridable like everything
#: else here.
DEFAULT_RATE_WINDOW_SECONDS = 60.0

#: What a credential renders as. Short, and obviously not a value.
MASK = "***"

#: Storage properties whose value is a secret rather than an identifier. An
#: access key id names a key; it does not open anything.
_SECRET_PROPERTIES = frozenset({"s3.secret-access-key"})


class InvalidRateLimit(ValueError):
    """A limit that permits nothing, or a window with no length.

    Refused rather than accepted: "allow zero requests per minute" takes the API
    down in a way that reads, from outside, as a bug in the API.
    """


class WildcardOrigin(ValueError):
    """CORS was configured to allow any origin.

    Refused where the configuration is read, beside `MissingConfiguration`,
    rather than warned about at the middleware. §34 requires CORS to be
    restricted in production, and a wildcard among named origins is still a
    wildcard.
    """


@dataclass(frozen=True)
class RateLimit:
    """How many requests a client may make, and over how long."""

    requests: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.requests <= 0:
            raise InvalidRateLimit(
                f"a limit of {self.requests} requests permits nothing; leave "
                f"{RATE_LIMIT} unset to run without a limit"
            )
        if self.window_seconds <= 0:
            raise InvalidRateLimit(f"a window of {self.window_seconds}s has no length")


def mask_password(uri: str) -> str:
    """A URI with its password replaced, and everything else intact.

    Parsed by position rather than split on punctuation. A password may contain
    `@` and `:` -- `p@ss:w@rd` is legal -- and a split on either finds the wrong
    separator and does so silently, leaving part of the secret in the output.
    The userinfo ends at the **last** `@` before the path; the password begins at
    the **first** `:` inside it.
    """
    scheme, separator, rest = uri.partition("://")
    if not separator:
        return uri
    netloc, slash, path = rest.partition("/")
    userinfo, at, host = netloc.rpartition("@")
    if not at:
        return uri
    user, colon, _password = userinfo.partition(":")
    if not colon:
        return uri
    return f"{scheme}://{user}:{MASK}@{host}{slash}{path}"


class MissingConfiguration(RuntimeError):
    """A required variable is unset.

    Raised rather than defaulted: the default that would be convenient here is a
    local directory, and a process serving an empty warehouse looks exactly like
    a market where nothing happened.
    """


@dataclass(frozen=True)
class Settings:
    """Everything the API needs to reach its data, and what it may refuse.

    `repr` and `str` are the same masked text. Two spellings would mean one of
    them is the unmasked one, and whichever it is would be the one that ends up
    in a log.
    """

    catalog_uri: str
    warehouse: str
    storage: Mapping[str, str]
    #: CORS origins. Empty means no allowance at all, which is a restriction
    #: rather than a missing setting.
    allowed_origins: tuple[str, ...] = ()
    #: `None` means unlimited -- a state that is chosen by leaving the variable
    #: unset, never arrived at by a parse failure.
    rate_limit: RateLimit | None = None

    def _rendered(self) -> str:
        storage = {
            key: MASK if key in _SECRET_PROPERTIES else value
            for key, value in sorted(self.storage.items())
        }
        return (
            f"Settings(catalog_uri={mask_password(self.catalog_uri)!r}, "
            f"warehouse={self.warehouse!r}, storage={storage!r}, "
            f"allowed_origins={self.allowed_origins!r}, rate_limit={self.rate_limit!r})"
        )

    def __repr__(self) -> str:
        return self._rendered()

    def __str__(self) -> str:
        return self._rendered()


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
        allowed_origins=_origins(values.get(CORS_ORIGINS, "")),
        rate_limit=_rate_limit(values),
    )


def _origins(raw: str) -> tuple[str, ...]:
    """The configured origins, refusing a wildcard among them."""
    origins = tuple(part.strip() for part in raw.split(",") if part.strip())
    if any(origin == "*" for origin in origins):
        raise WildcardOrigin(
            f"{CORS_ORIGINS} contains '*', which allows every origin; §34 requires "
            "CORS to be restricted. Name the origins, or leave it unset to allow none"
        )
    return origins


def _rate_limit(values: Mapping[str, str]) -> RateLimit | None:
    """The configured limit, or `None` for unlimited.

    Unset means unlimited and says so. A default number here would be a trading
    threshold compiled in, which Principle X forbids, and a deployment would
    inherit a limit nobody chose.
    """
    raw = values.get(RATE_LIMIT, "").strip()
    if not raw:
        return None
    window = values.get(RATE_WINDOW_SECONDS, "").strip()
    return RateLimit(
        requests=int(raw),
        window_seconds=float(window) if window else DEFAULT_RATE_WINDOW_SECONDS,
    )
