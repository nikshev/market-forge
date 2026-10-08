# @trace: REQ-INFRA-006
"""Re-read the recorded deployment from the chain; exit 1 saying which check differs (FR-012).

    python -m tools.notary.verify      # also: make notary-verify

It trusts neither the record nor the chain alone: the record's transaction must have a successful
receipt that created the recorded address, the code at that address must hash to the recorded value
*and* to a fresh local compile of `contracts/`, and `owner()` must be the recorded owner. A missing
receipt means "not deployed", never success.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

from tools.notary import record as record_file
from tools.notary.chain import Chain, ChainPort, Config, ConfigError, subprocess_runner
from tools.notary.deploy import poll


class VerifyError(RuntimeError):
    """The recorded deployment is not what the chain holds; the message says which check differs."""


def verify(
    chain: ChainPort,
    config: Config,
    *,
    record_path: Path,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    record = record_file.read(record_path)
    if record is None:
        raise VerifyError(f"no deployment record at {record_path}: nothing has been deployed")

    actual = chain.chain_id()
    if actual != record["chain_id"] or actual != config.chain_id:
        raise VerifyError(
            f"chain id differs: node reports {actual}, record {record['chain_id']}, "
            f"configured {config.chain_id}"
        )

    receipt = poll(lambda: chain.receipt(record["tx_hash"]), lambda r: r is not None, sleep)
    if receipt is None:
        raise VerifyError(
            f"no receipt for {record['tx_hash']}: not deployed (or the testnet was reset)"
        )
    if receipt.status != 1:
        raise VerifyError(f"receipt status is {receipt.status} (failed)")
    if (receipt.contract_address or "").lower() != record["address"].lower():
        raise VerifyError(
            f"address differs: receipt created {receipt.contract_address}, "
            f"record {record['address']}"
        )

    code_hash = chain.code_hash(record["address"])
    if code_hash != record["deployed_code_hash"]:
        raise VerifyError(
            f"code differs from the record: chain {code_hash}, "
            f"record {record['deployed_code_hash']}"
        )
    compiled = chain.expected_code_hash()
    if code_hash != compiled:
        raise VerifyError(
            f"deployed code differs from the compiled source: chain {code_hash}, local {compiled}"
        )

    owner = chain.owner_of(record["address"])
    if owner.lower() != record["owner"].lower():
        raise VerifyError(f"owner differs: contract says {owner}, record {record['owner']}")


def main() -> int:
    try:
        config = Config.from_env(os.environ)
        chain = Chain(
            config, runner=subprocess_runner, contracts_dir=record_file.ROOT / "contracts"
        )
        verify(chain, config, record_path=record_file.RECORD_PATH)
    except (ConfigError, VerifyError) as error:
        print(f"verify: FAILED -- {error}", file=sys.stderr)
        return 1
    record = record_file.read(record_file.RECORD_PATH) or {}
    print(
        f"verify: ok -- {record.get('address')} on chain {record.get('chain_id')} "
        "matches the record and the source"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
