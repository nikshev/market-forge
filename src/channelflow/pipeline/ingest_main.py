"""How the ingest daemon starts.

# @trace: REQ-WP-066
# @trace: REQ-WP-078
# @trace: REQ-WP-076

The same shape as the read API's composition root, and for the same reasons: the
environment is the only input, nothing defaults, and a missing variable refuses
to start rather than filling an empty warehouse that reads as a quiet market.
"""

from __future__ import annotations

import logging
import math
import os
import time
from collections.abc import Mapping
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from typing import Any

from channelflow.bars.builder import BarBuilder
from channelflow.connectors.session import StreamSession
from channelflow.connectors.venue import VENUE_REGISTRY
from channelflow.connectors.websocket import binance_stream_url
from channelflow.lakehouse import catalog as open_catalog
from channelflow.pipeline.archive import FrameArchive, LocalObjectStore, ObjectStore, S3ObjectStore
from channelflow.pipeline.ingest import IngestDaemon
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import bars as bars_table

LOG_LEVEL = "CHANNELFLOW_LOG_LEVEL"

#: What `logging` accepts by name, and nothing it accepts by number or by alias: `10` and
#: `trace` are refused rather than guessed at.
_LEVELS: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def log_level_from_env(environ: Mapping[str, str] | None = None) -> int:
    """The root log level: `CHANNELFLOW_LOG_LEVEL`, case-insensitive, `INFO` when unset."""
    values = os.environ if environ is None else environ
    raw = values.get(LOG_LEVEL, "").strip()
    if not raw:
        return logging.INFO
    try:
        return _LEVELS[raw.upper()]
    except KeyError:
        raise MissingConfiguration(
            f"{LOG_LEVEL} is {raw!r}; expected one of {', '.join(_LEVELS)}"
        ) from None


def configure_logging(environ: Mapping[str, str] | None = None) -> None:
    """Set up the root logger. Called from `main()`, not at import.

    It used to run at import time, so importing this module -- as every test of it does --
    gave the root logger a handler and a level before anything had asked for one.
    """
    logging.basicConfig(
        level=log_level_from_env(environ),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


SYMBOLS = "CHANNELFLOW_INGEST_SYMBOLS"
ARCHIVE_URI = "CHANNELFLOW_ARCHIVE_URI"
TIMEFRAME = "CHANNELFLOW_INGEST_TIMEFRAME_NS"
INGEST_VENUE = "CHANNELFLOW_INGEST_VENUE"
#: How long a feed may be silent before the session reconnects, in seconds. Unset or blank
#: leaves the venue's own policy value (60 s on the three live venues, with the measured
#: basis written beside it in `connectors/session.py`).
MAX_SILENCE_SECONDS = "CHANNELFLOW_INGEST_MAX_SILENCE_SECONDS"
#: Retired. It multiplied `idle_timeout_ns`, which is how long the *venue* tolerates a
#: silent *client* -- a different quantity on each venue, and for Binance a stream lifetime.
#: Refused when set, so a deployment that still carries it does not believe it is honoured.
RETIRED_SILENCE_MULTIPLIER = "CHANNELFLOW_SILENCE_WINDOW_MULTIPLIER"

#: One minute. A chart shows its first candle a minute after the daemon starts
#: rather than fifteen, which is the difference between believing it works and
#: waiting to find out.
DEFAULT_TIMEFRAME_NS = 60_000_000_000

SYMBOLS_BYBIT = "CHANNELFLOW_INGEST_SYMBOLS_BYBIT"
SYMBOLS_OKX = "CHANNELFLOW_INGEST_SYMBOLS_OKX"


class SystemClock:
    """`StreamSession`'s clock, against the real one."""

    def now_ns(self) -> int:
        import time

        return time.time_ns()


@dataclass(frozen=True)
class IngestSettings:
    symbols: tuple[str, ...]
    archive_uri: str
    timeframe_ns: int
    #: `None` leaves the venue policy's own `max_silence_ns`.
    max_silence_ns: int | None = None


def ingest_settings_from_env(environ: Mapping[str, str] | None = None) -> IngestSettings:
    values = os.environ if environ is None else environ

    missing = [name for name in (SYMBOLS, ARCHIVE_URI) if not values.get(name, "").strip()]
    if missing:
        raise MissingConfiguration(
            f"{', '.join(missing)} must be set; a daemon with no symbols reads nothing "
            "and one with no archive keeps nothing, and both look like a quiet venue"
        )

    symbols = tuple(part.strip() for part in values[SYMBOLS].split(",") if part.strip())
    if not symbols:
        raise MissingConfiguration(f"{SYMBOLS} named no symbol")

    raw_timeframe = values.get(TIMEFRAME, "").strip()
    timeframe = int(raw_timeframe) if raw_timeframe else DEFAULT_TIMEFRAME_NS
    if timeframe <= 0:
        raise MissingConfiguration(f"{TIMEFRAME} must be positive, got {timeframe}")

    if values.get(RETIRED_SILENCE_MULTIPLIER, "").strip():
        raise MissingConfiguration(
            f"{RETIRED_SILENCE_MULTIPLIER} was removed: it multiplied a quantity that meant "
            f"something different on each venue. Set {MAX_SILENCE_SECONDS} (seconds) instead, "
            "or leave both unset for the venue's measured default"
        )

    raw_silence = values.get(MAX_SILENCE_SECONDS, "").strip()
    max_silence_ns: int | None = None
    if raw_silence:
        try:
            seconds = float(raw_silence)
        except ValueError:
            seconds = math.nan
        if not math.isfinite(seconds) or seconds <= 0:
            raise MissingConfiguration(
                f"{MAX_SILENCE_SECONDS} must be a positive number of seconds, got {raw_silence!r}"
            )
        max_silence_ns = int(seconds * 1_000_000_000)

    return IngestSettings(
        symbols=symbols,
        archive_uri=values[ARCHIVE_URI].strip(),
        timeframe_ns=timeframe,
        max_silence_ns=max_silence_ns,
    )


def object_store_for(uri: str, storage: Mapping[str, str]) -> ObjectStore:
    """`s3://bucket/...` or a directory. One seam, two implementations.

    The scheme decides, and nothing else does: the same line `lakehouse.catalog`
    draws between a local run and a deployment.
    """
    if not uri.startswith("s3://"):
        return LocalObjectStore(root=Path(uri))

    import boto3

    bucket = uri.removeprefix("s3://").split("/", 1)[0]
    client = boto3.client(
        "s3",
        endpoint_url=storage.get("s3.endpoint"),
        aws_access_key_id=storage.get("s3.access-key-id"),
        aws_secret_access_key=storage.get("s3.secret-access-key"),
        region_name=storage.get("s3.region"),
    )
    return S3ObjectStore(bucket=bucket, client=client)


def _resolve_connector(dotted: str) -> Any:
    """Import the connector class the registry names.

    The registry stores a dotted path rather than the class so importing the
    registry does not import every venue's dependencies. The return is `Any`
    deliberately: the three venues take different constructor arguments, so no
    single signature describes them, and a path that names something else fails
    loudly at startup, where a refusal to start is the documented behaviour.
    """
    module_name, _, class_name = dotted.rpartition(".")
    return getattr(import_module(module_name), class_name)


def build_daemon(
    *,
    symbol: str,
    settings: IngestSettings,
    store: ObjectStore,
    catalog_uri: str,
    warehouse: str,
    storage: Mapping[str, str],
    venue: str,
) -> IngestDaemon:
    """One symbol's daemon, wired from configuration."""
    if venue not in VENUE_REGISTRY:
        raise MissingConfiguration(f"Unknown venue: {venue}. Known: {list(VENUE_REGISTRY.keys())}")

    # Binance and Bybit name an instrument in upper case, and the archive key and the
    # migration both use that spelling. A symbol configured as `btcusdt` would put one
    # instrument in two directories. OKX's `BTC-USDT-SWAP` is already upper case.
    if venue in ("binance", "bybit") and symbol != symbol.upper():
        raise MissingConfiguration(
            f"{SYMBOLS} names {symbol!r} for {venue}; write it in upper case "
            f"({symbol.upper()!r}) so one instrument has one archive directory"
        )

    config = VENUE_REGISTRY[venue]
    catalog = open_catalog(uri=catalog_uri, warehouse=warehouse, **dict(storage))
    sink = bars_table.BarSink(table=bars_table.table_for(catalog))
    builder = BarBuilder(timeframe_ns=settings.timeframe_ns, on_final=sink)

    streams = config.stream_builder([symbol])
    connector_cls = _resolve_connector(config.connector)

    # Endpoint and subscription come from the registry and from nowhere else. They were
    # once spelled out here per venue, which is where OKX's URL answered `HTTP 404` and its
    # `instId` carried a stream-label prefix, beside tests that built the connector by hand.
    if config.url is None:
        connector = connector_cls(url_for=binance_stream_url)  # Binance subscribes by URL
    else:
        connector = connector_cls(url=config.url, subscribe_msg=config.subscribe_message([symbol]))

    policy = config.policy
    if settings.max_silence_ns is not None:
        try:
            policy = replace(policy, max_silence_ns=settings.max_silence_ns)
        except ValueError as error:
            raise MissingConfiguration(f"{MAX_SILENCE_SECONDS}: {error}") from error

    session = StreamSession(
        streams=streams, policy=policy, connector=connector, clock=SystemClock()
    )
    prefix = settings.archive_uri.removeprefix("s3://").split("/", 1)
    return IngestDaemon(
        session=session,
        connector=connector,
        archive=FrameArchive(
            store=store,
            venue=venue,
            symbol=symbol,
            # The path of the archive URI, unchanged. The venue is added **once**,
            # by `key_for`: prefixing it here as well filed every frame at the
            # bucket root as `<venue>/raw/cex/<venue>/...`, where nothing reads.
            prefix=prefix[1] if len(prefix) > 1 else "raw/cex",
        ),
        builder=builder,
        venue=venue,
        flush_bars=sink.flush,
        bars_pending=lambda: sink.pending,
        now_ns=lambda: time.time_ns(),
    )


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    plane = settings_from_env()
    ingest = ingest_settings_from_env()

    if not os.environ.get(INGEST_VENUE, "").strip():
        raise MissingConfiguration(f"{INGEST_VENUE} must be set (binance, bybit, or okx)")

    venue = os.environ[INGEST_VENUE].strip().lower()

    if len(ingest.symbols) > 1:
        # One process per symbol, deliberately. `BarBuilder` is one symbol and
        # one timeframe, and a daemon multiplexing several would own a decision
        # a deployment can make better -- and would share one socket's failure
        # across all of them.
        raise MissingConfiguration(
            f"{SYMBOLS} names {len(ingest.symbols)} symbols; run one process each"
        )

    store = object_store_for(ingest.archive_uri, plane.storage)
    daemon = build_daemon(
        symbol=ingest.symbols[0],
        settings=ingest,
        store=store,
        catalog_uri=plane.catalog_uri,
        warehouse=plane.warehouse,
        storage=plane.storage,
        venue=venue,
    )
    print(
        f"ingesting {ingest.symbols[0]} at {ingest.timeframe_ns / 1e9:g}s bars for {venue}, "
        f"archiving to {ingest.archive_uri}"
    )
    daemon.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
