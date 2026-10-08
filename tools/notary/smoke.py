# @trace: REQ-INFRA-006
"""One real commit and one real resolve on the deployed contract (FR-013).

    python -m tools.notary.smoke

Proves the deployed contract, not just the compiled one. The hash is a fixed-purpose smoke hash
derived from the contract address and the time, not a signal. Both transactions are read back
(receipt, event, stored state) before anything is written into the record's `smoke` block.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tools.notary import record as record_file
from tools.notary.chain import Chain, ChainPort, Config, ConfigError, subprocess_runner
from tools.notary.deploy import poll

COMMITTED = "Committed(bytes32,uint64,address)"
RESOLVED = "Resolved(bytes32,uint8)"
TARGET_HIT = 1


class SmokeError(RuntimeError):
    """A read-back of the smoke transactions disagreed; nothing is recorded."""


def _confirm(
    chain: ChainPort, tx_hash: str, event: str, hash_: str, sleep: Callable[[float], None]
) -> None:
    receipt = poll(lambda: chain.receipt(tx_hash), lambda r: r is not None, sleep)
    if receipt is None or receipt.status != 1:
        raise SmokeError(f"transaction {tx_hash} has no successful receipt")
    topic = chain.keccak(event)
    if not any(log.topics[:2] == (topic, hash_) for log in receipt.logs):
        raise SmokeError(f"the {event.split('(')[0]} event for {hash_} is not in {tx_hash}")


def smoke(
    chain: ChainPort,
    config: Config,
    *,
    record_path: Path,
    now: Callable[[], int] = lambda: int(time.time()),
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    record = record_file.read(record_path)
    if record is None:
        raise SmokeError(f"no deployment record at {record_path}: deploy first")
    if "smoke" in record:
        raise SmokeError("a smoke run is already recorded; it is written once")
    address = record["address"]
    signer = chain.signer_address()

    bar_ts = now()
    hash_ = chain.keccak(f"signal-notary-smoke:{address}:{bar_ts}")

    commit_tx = chain.send(address, "commit(bytes32,uint64)", (hash_, str(bar_ts)))
    _confirm(chain, commit_tx, COMMITTED, hash_, sleep)
    stored_bar, stored_block, committer = poll(
        lambda: chain.commit_of(address, hash_), lambda c: c[2].lower() == signer.lower(), sleep
    )
    if stored_bar != bar_ts or committer.lower() != signer.lower():
        raise SmokeError(
            f"commit read-back differs: stored barTs {stored_bar} committer {committer}, "
            f"sent barTs {bar_ts} from {signer}"
        )

    resolve_tx = chain.send(address, "resolve(bytes32,uint8)", (hash_, str(TARGET_HIT)))
    _confirm(chain, resolve_tx, RESOLVED, hash_, sleep)
    outcome = poll(lambda: chain.outcome_of(address, hash_), lambda o: o == TARGET_HIT, sleep)
    if outcome != TARGET_HIT:
        raise SmokeError(f"resolve read-back differs: stored outcome {outcome}, sent {TARGET_HIT}")

    block = {
        "hash": hash_,
        "bar_ts": bar_ts,
        "commit_tx": commit_tx,
        "commit_block_time": stored_block,
        "resolve_tx": resolve_tx,
        "outcome": outcome,
    }
    record_file.write(record_path, {**record, "smoke": block})
    return block


def main() -> int:
    try:
        config = Config.from_env(os.environ)
        chain = Chain(
            config, runner=subprocess_runner, contracts_dir=record_file.ROOT / "contracts"
        )
        block = smoke(chain, config, record_path=record_file.RECORD_PATH)
    except (ConfigError, SmokeError) as error:
        print(f"smoke: FAILED -- {error}", file=sys.stderr)
        return 1
    base = Config.from_env(os.environ).explorer_url
    print(
        f"smoke: ok\n  commit  {base}/tx/{block['commit_tx']}\n"
        f"  resolve {base}/tx/{block['resolve_tx']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
