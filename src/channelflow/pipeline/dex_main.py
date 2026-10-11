"""The DEX collector's entrypoint: HyperEVM's two WHYPE/USDC pools (REQ-WP-099).

# @trace: REQ-WP-099

    python -m channelflow.pipeline.dex_main

Reads HyperEVM's public JSON-RPC (`CHANNELFLOW_DEX_RPC_URL`; no key), stores each swap of the two
registered pools in `dex_swaps` and a reading of each pool every poll in `dex_state`. Serves
`/healthz` and `/metrics` on `CHANNELFLOW_DEX_PORT`. The worker is the only writer of features
([[ADR-070]]); this process writes raw tables only.

On start it resumes after the last block already stored, so a restart neither repeats a swap nor
skips the ones that happened while it was down (up to the node's reach: a first run starts five
minutes back).
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import FrameType

from channelflow.connectors.hyperevm.rpc import HyperEvmNode, JsonRpcClient
from channelflow.context.status import Status, serve
from channelflow.dex import hyperevm_pools as registry
from channelflow.dex.hyperevm_collect import POLL_INTERVAL_S, DexCollector
from channelflow.lakehouse import catalog as open_catalog
from channelflow.settings import MissingConfiguration, settings_from_env
from channelflow.tables import dex_state, dex_swaps

RPC_URL = "CHANNELFLOW_DEX_RPC_URL"
PORT = "CHANNELFLOW_DEX_PORT"
LOG_LEVEL = "CHANNELFLOW_LOG_LEVEL"

DEFAULT_RPC_URL = "https://rpc.hyperliquid.xyz/evm"
DEFAULT_PORT = 9104


@dataclass(frozen=True)
class DexSettings:
    rpc_url: str
    port: int


def dex_settings_from_env(environ: Mapping[str, str] | None = None) -> DexSettings:
    values = os.environ if environ is None else environ
    url = values.get(RPC_URL, "").strip() or DEFAULT_RPC_URL
    if not url.startswith(("http://", "https://")):
        raise MissingConfiguration(f"{RPC_URL} is {url!r}; expected an http(s) URL")
    raw_port = values.get(PORT, "").strip()
    try:
        port = int(raw_port) if raw_port else DEFAULT_PORT
    except ValueError:
        raise MissingConfiguration(f"{PORT} is {raw_port!r}; expected a port number") from None
    if not 0 < port < 65536:
        raise MissingConfiguration(f"{PORT} is {port}; expected 1-65535")
    return DexSettings(rpc_url=url, port=port)


def last_stored_block(rows: Iterable[Mapping[str, object]], *, chain_id: int) -> int | None:
    """The highest block of this chain among stored swaps, or `None` if there are none."""
    blocks = [int(str(row["block_number"])) for row in rows if row["chain_id"] == chain_id]
    return max(blocks) if blocks else None


def main(argv: list[str] | None = None) -> int:
    level = os.environ.get(LOG_LEVEL, "").strip().upper() or "INFO"
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = dex_settings_from_env()
    plane = settings_from_env()

    catalog = open_catalog(uri=plane.catalog_uri, warehouse=plane.warehouse, **dict(plane.storage))
    swap_table = dex_swaps.table_for(catalog)
    stored = swap_table.read().select(["chain_id", "block_number"]).to_pylist()
    cursor = last_stored_block(stored, chain_id=registry.CHAIN_ID)

    status = Status(venue="hyperevm", poll_interval_s=POLL_INTERVAL_S, now_ns=time.time_ns)
    rpc = JsonRpcClient(settings.rpc_url)
    collector = DexCollector(
        node=HyperEvmNode(rpc),
        swaps=dex_swaps.DexSwapSink(swap_table),
        states=dex_state.DexStateSink(dex_state.table_for(catalog)),
        status=status,
        now_ns=time.time_ns,
        cursor=cursor,
    )
    server, _ = serve(status, port=settings.port)
    stop = threading.Event()

    def _stop(signum: int, frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    print(
        f"collecting HyperEVM swaps of {len(registry.POOLS)} pools every {POLL_INTERVAL_S}s from "
        f"block {'(start: five minutes back)' if cursor is None else cursor + 1}; "
        f"health on :{settings.port}",
        flush=True,
    )
    try:
        collector.run(stop)
    finally:
        server.shutdown()
        server.server_close()
        rpc.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
