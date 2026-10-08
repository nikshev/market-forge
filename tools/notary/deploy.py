# @trace: REQ-INFRA-006
"""Deploy SignalNotary, read the deployment back, and only then write the record (FR-010, FR-011).

    python -m tools.notary.deploy              # a dry run: what would be sent, nothing is
    python -m tools.notary.deploy --broadcast  # the real deployment

A dry run is the default because the deployment spends funds and publishes an address. `--broadcast`
additionally refuses a dirty `contracts/` tree, so that the recorded `source_commit` is the code
that ran.

The record is written **last**: only after the receipt succeeded, the created address matched, the
code on the chain hashed to the locally compiled runtime bytecode, and `owner()` returned the
intended owner. Nothing in the repository may claim a deployment that did not happen.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from tools.notary import record as record_file
from tools.notary.chain import (
    Chain,
    ChainMismatch,
    ChainPort,
    Config,
    ConfigError,
    subprocess_runner,
)

#: Below this the deployment is refused (0.1 MON; a create costs a small fraction of it).
MIN_BALANCE_WEI = 10**17
POLL_TRIES = 6
POLL_SECONDS = 2.0


class DeployError(RuntimeError):
    """A read-back check failed; the message names which one."""


class Repo(Protocol):
    def contracts_clean(self) -> bool: ...
    def head(self) -> str: ...


class GitRepo:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self._root), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    def contracts_clean(self) -> bool:
        return self._git("status", "--porcelain", "--", "contracts") == ""

    def head(self) -> str:
        return self._git("rev-parse", "HEAD")


def poll[T](read: Callable[[], T], good: Callable[[T], bool], sleep: Callable[[float], None]) -> T:
    """Read until `good`, at most POLL_TRIES times: a load-balanced node can lag a block."""
    value = read()
    for _ in range(POLL_TRIES - 1):
        if good(value):
            break
        sleep(POLL_SECONDS)
        value = read()
    return value


def deploy(
    chain: ChainPort,
    config: Config,
    repo: Repo,
    *,
    broadcast: bool,
    record_path: Path,
    out: Callable[[str], None] = print,
    sleep: Callable[[float], None] = time.sleep,
    contracts_dir: Path = record_file.ROOT / "contracts",
) -> dict[str, Any] | None:
    actual = chain.chain_id()
    if actual != config.chain_id:
        raise ChainMismatch(
            f"configured chain id is {config.chain_id} but the node at {config.rpc_url} "
            f"reports {actual}"
        )

    deployer = chain.signer_address()
    owner = config.owner or deployer
    balance = chain.balance_wei(deployer)
    expected_hash = chain.expected_code_hash()
    out(f"chain id      {actual}")
    out(f"rpc           {config.rpc_url}")
    out(f"deployer      {deployer}")
    out(f"owner         {owner}")
    out(f"balance       {balance / 10**18:.6f} MON")
    out(f"compiled code {expected_hash}")
    out(f"contracts/    {'clean' if repo.contracts_clean() else 'DIRTY'}")

    if not broadcast:
        out("dry run: nothing was sent (pass --broadcast to deploy)")
        return None
    if not repo.contracts_clean():
        raise DeployError(
            "contracts/ has uncommitted changes; commit them so source_commit is what ran"
        )
    if balance < MIN_BALANCE_WEI:
        raise DeployError(f"balance {balance} wei is below the minimum {MIN_BALANCE_WEI} wei")

    tx_hash, address = chain.create(owner)
    out(f"sent          {tx_hash}")

    receipt = poll(lambda: chain.receipt(tx_hash), lambda r: r is not None, sleep)
    if receipt is None:
        raise DeployError(f"no receipt for {tx_hash} after {POLL_TRIES} reads; nothing is recorded")
    if receipt.status != 1:
        raise DeployError(f"receipt status is {receipt.status} (failed) for {tx_hash}")
    if (receipt.contract_address or "").lower() != address.lower():
        raise DeployError(
            f"created address differs: receipt says {receipt.contract_address}, "
            f"deployer printed {address}"
        )
    if receipt.sender.lower() != deployer.lower():
        raise DeployError(f"sender differs: receipt {receipt.sender}, expected {deployer}")

    code_hash = poll(lambda: chain.code_hash(address), lambda h: h == expected_hash, sleep)
    if code_hash != expected_hash:
        raise DeployError(
            "deployed code differs from the compiled source: "
            f"chain {code_hash}, local {expected_hash}"
        )
    on_chain_owner = poll(
        lambda: chain.owner_of(address), lambda o: o.lower() == owner.lower(), sleep
    )
    if on_chain_owner.lower() != owner.lower():
        raise DeployError(f"owner differs: contract says {on_chain_owner}, intended {owner}")

    record = {
        "chain_id": actual,
        "address": address,
        "tx_hash": tx_hash,
        "block_number": receipt.block_number,
        "block_time": chain.block_time(receipt.block_number),
        "owner": on_chain_owner,
        "deployer": deployer,
        "source_commit": repo.head(),
        "solc": record_file.solc_version(contracts_dir),
        "deployed_code_hash": code_hash,
    }
    record_file.write(record_path, record)
    out("read back     receipt ok, address, code and owner match")
    out(f"recorded      {record_path}")
    out(f"add to .env.example:  MONAD_NOTARY_ADDRESS={address}")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--broadcast", action="store_true", help="really deploy (default is a dry run)"
    )
    args = parser.parse_args(argv)
    try:
        config = Config.from_env(os.environ)
        chain = Chain(
            config, runner=subprocess_runner, contracts_dir=record_file.ROOT / "contracts"
        )
        deploy(
            chain,
            config,
            GitRepo(record_file.ROOT),
            broadcast=args.broadcast,
            record_path=record_file.RECORD_PATH,
        )
    except (ConfigError, DeployError, ChainMismatch) as error:
        print(f"deploy: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
