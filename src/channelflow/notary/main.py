"""The notary service: form batches, send them, confirm them, and say what waits (REQ-INFRA-007).

# @trace: REQ-INFRA-007

    python -m channelflow.notary.main            # run: loop until stopped
    python -m channelflow.notary.main --once     # one tick and exit
    python -m channelflow.notary.main outbox     # what waits, and why; no chain, no key

This is the only process that holds the signing key, which it reads from a mounted keystore and
password file. It starts only if the node is on the configured chain and the signing address is the
contract's owner; otherwise it exits with the reason, so that a misconfigured deployment is a
crash-looping container rather than a service that quietly signs transactions the contract rejects.
"""

from __future__ import annotations

import argparse
import http.server
import os
import re
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.metrics import MetricKind, MetricRegistry
from channelflow.notary import tables
from channelflow.notary.chain import (
    ChainDown,
    JsonRpcChain,
    NotaryChain,
    http_transport,
    load_signer,
)
from channelflow.notary.config import ConfigError, parse_duration_s
from channelflow.notary.submitter import (
    Submitter,
    SubmitterConfig,
    outbox_states,
    outbox_summary,
)
from channelflow.pipeline.passes import run_passes
from channelflow.settings import settings_from_env

SECOND_NS = 1_000_000_000
_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")

DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz"
DEFAULT_CHAIN_ID = 10143


@dataclass(frozen=True)
class ServiceConfig:
    rpc_url: str
    chain_id: int
    contract: str
    deploy_block: int
    keystore: Path
    password_file: Path
    gas_margin: float
    interval_s: float
    metrics_port: int
    submitter: SubmitterConfig

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> ServiceConfig:
        def required(name: str) -> str:
            value = env.get(name, "").strip()
            if not value:
                raise ConfigError(f"{name} must be set")
            return value

        def integer(name: str, default: int | None, *, minimum: int) -> int:
            raw = env.get(name, "").strip()
            if not raw and default is None:
                raise ConfigError(f"{name} must be set")
            try:
                value = int(raw) if raw else int(str(default))
            except ValueError as error:
                raise ConfigError(f"{name} is not an integer: {raw!r}") from error
            if value < minimum:
                raise ConfigError(f"{name} must be at least {minimum}, not {value}")
            return value

        def duration(name: str, default: str) -> float:
            seconds = parse_duration_s(env.get(name, "").strip() or default, name=name)
            if seconds <= 0:
                raise ConfigError(f"{name} must be positive")
            return seconds

        contract = required("MONAD_NOTARY_ADDRESS")
        if not _ADDRESS.match(contract):
            raise ConfigError(f"MONAD_NOTARY_ADDRESS is not an address: {contract!r}")
        margin_raw = env.get("CHANNELFLOW_NOTARY_GAS_MARGIN", "").strip() or "1.05"
        try:
            margin = float(margin_raw)
        except ValueError as error:
            raise ConfigError(
                f"CHANNELFLOW_NOTARY_GAS_MARGIN is not a number: {margin_raw!r}"
            ) from error
        if margin < 1.0:
            raise ConfigError(
                f"CHANNELFLOW_NOTARY_GAS_MARGIN is {margin}; below 1 the limit is under the "
                "estimate and the transaction runs out of gas, which on Monad still costs the "
                "whole limit"
            )
        return cls(
            rpc_url=env.get("MONAD_RPC_URL", "").strip() or DEFAULT_RPC_URL,
            chain_id=integer("MONAD_CHAIN_ID", DEFAULT_CHAIN_ID, minimum=1),
            contract=contract,
            deploy_block=integer("MONAD_NOTARY_DEPLOY_BLOCK", None, minimum=0),
            keystore=Path(required("CHANNELFLOW_NOTARY_KEYSTORE")),
            password_file=Path(required("CHANNELFLOW_NOTARY_PASSWORD_FILE")),
            gas_margin=margin,
            interval_s=duration("CHANNELFLOW_NOTARY_INTERVAL", "60"),
            metrics_port=integer("CHANNELFLOW_NOTARY_METRICS_PORT", 8000, minimum=1),
            submitter=SubmitterConfig(
                window_ns=int(duration("CHANNELFLOW_NOTARY_BATCH_WINDOW", "30m") * SECOND_NS),
                max_batch=integer("CHANNELFLOW_NOTARY_MAX_BATCH", 5000, minimum=1),
                min_balance_wei=integer("CHANNELFLOW_NOTARY_MIN_BALANCE", 10**17, minimum=0),
                max_gas_price_wei=integer(
                    "CHANNELFLOW_NOTARY_MAX_GAS_PRICE", 500 * 10**9, minimum=1
                ),
                submit_timeout_ns=int(
                    duration("CHANNELFLOW_NOTARY_SUBMIT_TIMEOUT", "120") * SECOND_NS
                ),
            ),
        )


# ---- the visible outbox -----------------------------------------------------------------------


def render_outbox(catalog: Catalog, *, now_ns: int) -> str:
    summary = outbox_summary(catalog, now_ns=now_ns)
    lines = [
        f"unbatched records: {summary.unbatched_records}",
        f"unconfirmed batches: {summary.unconfirmed_batches}",
        f"unnotarizable records: {summary.unnotarizable_records}",
        f"oldest pending: {summary.oldest_pending_age_s:.0f} s",
        f"last error: {summary.last_error or '-'}",
    ]
    for batch, state in outbox_states(catalog):
        if state["event"] != "confirmed":
            lines.append(
                f"  batch {str(batch['batch_root'])[:12]}  {state['event']}  "
                f"attempt {state['attempt']}  {state['detail']}"
            )
    for row in tables.unnotarizable(tables.records_table(catalog)):
        lines.append(f"  unnotarizable {row['record_id']}: {row['reason']}")
    return "\n".join(lines)


# ---- metrics ----------------------------------------------------------------------------------

GAUGES = {
    "channelflow_notary_unbatched_records": "Registered records not yet in any batch.",
    "channelflow_notary_unconfirmed_batches": "Batches formed and not yet confirmed on the chain.",
    "channelflow_notary_oldest_pending_age_seconds": "Age of the oldest unconfirmed record.",
    "channelflow_notary_unnotarizable_records": "Records stored without a hash, with a reason.",
    "channelflow_notary_balance_wei": "The signing account's balance. Absent when unknown.",
    "channelflow_notary_last_confirmed_block_time_seconds": "Block time of the latest commit.",
}


def new_registry() -> MetricRegistry:
    registry = MetricRegistry()
    for name, help_text in GAUGES.items():
        registry.register(name, MetricKind.GAUGE, help_text)
    return registry


def update_metrics(
    registry: MetricRegistry, catalog: Catalog, chain: NotaryChain, *, now_ns: int
) -> None:
    summary = outbox_summary(catalog, now_ns=now_ns)
    registry.observe("channelflow_notary_unbatched_records", summary.unbatched_records)
    registry.observe("channelflow_notary_unconfirmed_batches", summary.unconfirmed_batches)
    registry.observe("channelflow_notary_oldest_pending_age_seconds", summary.oldest_pending_age_s)
    registry.observe("channelflow_notary_unnotarizable_records", summary.unnotarizable_records)
    confirmed = [
        int(str(s["block_time_s"])) for _, s in outbox_states(catalog) if s["event"] == "confirmed"
    ]
    if confirmed:
        registry.observe("channelflow_notary_last_confirmed_block_time_seconds", max(confirmed))
    try:
        registry.observe("channelflow_notary_balance_wei", chain.balance_wei())
    except ChainDown:
        pass  # unknown is not zero: the gauge keeps its last reading, or stays absent


def start_metrics_server(registry: MetricRegistry, port: int) -> http.server.ThreadingHTTPServer:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 -- the stdlib's name
            if self.path != "/metrics":
                self.send_error(404)
                return
            body = (registry.render() + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass

    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), Handler)  # noqa: S104 -- in-container
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ---- the loop ---------------------------------------------------------------------------------


def serve(
    submitter: Submitter,
    catalog: Catalog,
    chain: NotaryChain,
    registry: MetricRegistry,
    *,
    interval_s: float | None,
    sleep: Callable[[float], object] | None = None,
) -> int:
    """Tick until stopped. `run_passes` reports a failed tick and goes on; so does this."""

    def one_tick() -> None:
        report = submitter.tick()
        for error in report.errors:
            print(f"-- notary: {error}", flush=True)
        if report.sent or report.confirmed or report.formed or report.held:
            print(
                f"-- notary: formed {report.formed}, sent {report.sent}, "
                f"confirmed {report.confirmed}, held {report.held}",
                flush=True,
            )
        update_metrics(registry, catalog, chain, now_ns=time.time_ns())

    return run_passes("notary", one_tick, interval_seconds=interval_s, sleep=sleep)


def main(argv: list[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    environment = os.environ if env is None else env
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", nargs="?", choices=["run", "outbox"], default="run")
    parser.add_argument("--once", action="store_true", help="one tick and exit")
    args = parser.parse_args(argv)

    try:
        settings = settings_from_env(environment)
        catalog = open_catalog(
            uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
        )
        if args.command == "outbox":
            print(render_outbox(catalog, now_ns=time.time_ns()))
            return 0

        config = ServiceConfig.from_env(environment)
        signer = load_signer(config.keystore, config.password_file)
        chain = JsonRpcChain(
            http_transport(config.rpc_url),
            chain_id=config.chain_id,
            contract=config.contract,
            account=signer,
            gas_margin=config.gas_margin,
            from_block=config.deploy_block,
        )
        chain.verify_ready()
    except Exception as error:  # noqa: BLE001 -- say what is wrong and exit; never a stack of secrets
        print(f"notary: cannot start: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print(
        f"notary: signing as {signer.address} for {config.contract} on chain {config.chain_id}",
        flush=True,
    )
    registry = new_registry()
    start_metrics_server(registry, config.metrics_port)
    submitter = Submitter(
        catalog=catalog, chain=chain, config=config.submitter, now_ns=time.time_ns
    )
    return serve(
        submitter, catalog, chain, registry, interval_s=None if args.once else config.interval_s
    )


if __name__ == "__main__":
    raise SystemExit(main())
