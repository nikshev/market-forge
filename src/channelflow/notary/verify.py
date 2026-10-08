"""Checking a record against the chain, and handing someone the means to (REQ-INFRA-007).

# @trace: REQ-INFRA-007

Three things, in increasing distance from this system:

* `verify_record` -- a record in our lakehouse: look it up, build its bundle, check the bundle;
* `export_bundle` -- everything a third party needs, as JSON: the record's canonical bytes, the
  three context values, the inclusion proof, the root and where to look;
* `verify_bundle` -- needs **only the bundle and a public node**. It recomputes the record hash from
  the bytes and the context, checks the inclusion proof, then asks the chain, independently, whether
  the root is there and at what time. The bundle's own `commit` block is a claim; it is not read.

What a pass proves is stated once and exactly: the record existed **no later than** the block that
holds its root. It says nothing about any price move, and nothing here may suggest it does.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from channelflow.lakehouse import Catalog
from channelflow.lakehouse import catalog as open_catalog
from channelflow.notary import tables
from channelflow.notary.chain import JsonRpcChain, NotaryChain, http_transport
from channelflow.notary.scheme import (
    SCHEME_VERSION,
    Context,
    inclusion_proof,
    record_hash_hex,
    verify_inclusion,
)
from channelflow.notary.submitter import outbox_states
from channelflow.settings import settings_from_env

SECOND_NS = 1_000_000_000

NO_LATER = (
    "The block time shows the record existed no later than that block. It does not show that the "
    "record preceded any price move."
)


@dataclass(frozen=True)
class VerifyResult:
    status: str  # committed | pending | not committed
    record_id: str
    detail: str
    root: str = ""
    block_number: int = -1
    block_time: int = -1
    tx_hash: str = ""
    latency_s: int | None = None


def bar_close_from_record_bytes(data: bytes) -> int:
    """The first column of every notarized row is its bar close, a `timestamp_ns`.

    Read from the record's own bytes -- not from a field next to them -- so the latency a verifier
    reports is about the thing that was hashed.
    """
    if len(data) < 13 or struct.unpack_from("<I", data, 1)[0] != 8:
        raise ValueError("the record does not start with an 8-byte time column")
    value: int = struct.unpack_from("<q", data, 5)[0]
    return value


def _not_committed(record_id: str, detail: str, **extra: Any) -> VerifyResult:
    return VerifyResult("not committed", record_id, detail, **extra)


def export_bundle(
    catalog: Catalog,
    record_id: str,
    *,
    chain_id: int,
    contract: str,
    rpc_hint: str,
    deploy_block: int = 0,
) -> dict[str, Any]:
    """The bundle of `contracts/notary-bundle.md`. Raises if the record is not yet in a batch."""
    record = next(
        (
            r
            for r in tables.records_table(catalog).read().to_pylist()
            if r["record_id"] == record_id
        ),
        None,
    )
    if record is None:
        raise KeyError(f"no such record: {record_id}")
    if record["notarizable"] != "yes":
        raise ValueError(f"{record_id} is unnotarizable: {record['reason']}")
    leaves = tables.leaves_table(catalog).read().to_pylist()
    mine = next((leaf for leaf in leaves if leaf["record_id"] == record_id), None)
    if mine is None:
        raise ValueError(f"{record_id} is not yet in a batch")
    root = str(mine["batch_root"])
    members = sorted(
        (leaf for leaf in leaves if leaf["batch_root"] == root), key=lambda x: x["ordinal"]
    )
    hashes = [bytes.fromhex(str(leaf["record_hash"])) for leaf in members]
    index = int(mine["ordinal"])

    states = {str(b["batch_root"]): s for b, s in outbox_states(catalog)}
    state = states.get(root)
    commit = (
        {
            "tx_hash": state["tx_hash"],
            "block_number": state["block_number"],
            "block_time": state["block_time_s"],
        }
        if state is not None and state["event"] == "confirmed"
        else {}
    )
    return {
        "scheme_version": int(record["scheme_version"]),
        "record": {
            "record_id": record_id,
            "kind": record["kind"],
            "record_bytes": record["record_bytes"],
        },
        "context": {
            "config_hash": record["config_hash"],
            "dataset_ref": record["dataset_ref"],
            "code_commit": record["code_commit"],
        },
        "record_hash": record["record_hash"],
        "inclusion": {
            "leaf_index": index,
            "tree_size": len(hashes),
            "path": [step.hex() for step in inclusion_proof(hashes, index)],
        },
        "root": root,
        "chain": {
            "chain_id": chain_id,
            "contract": contract,
            "rpc_hint": rpc_hint,
            # Where a verifier may start looking for the commit's block; 0 is safe, only slower.
            "deploy_block": deploy_block,
        },
        "commit": commit,
    }


def verify_bundle(bundle: dict[str, Any], chain: NotaryChain) -> VerifyResult:
    record = bundle["record"]
    record_id = str(record["record_id"])
    context = bundle["context"]

    recomputed = record_hash_hex(
        str(record["kind"]),
        bytes.fromhex(str(record["record_bytes"])),
        Context(
            config_hash=str(context["config_hash"]),
            dataset_ref=str(context["dataset_ref"]),
            code_commit=str(context["code_commit"]),
        ),
        version=int(bundle.get("scheme_version", SCHEME_VERSION)),
    )
    if recomputed != bundle["record_hash"]:
        return _not_committed(
            record_id, "the record hash does not match the record and its context"
        )

    inclusion = bundle["inclusion"]
    root = str(bundle["root"])
    if not verify_inclusion(
        bytes.fromhex(recomputed),
        int(inclusion["leaf_index"]),
        int(inclusion["tree_size"]),
        [bytes.fromhex(step) for step in inclusion["path"]],
        bytes.fromhex(root),
    ):
        return _not_committed(
            record_id, "the inclusion proof does not verify against the root", root=root
        )

    if chain.chain_id() != int(bundle["chain"]["chain_id"]):
        return _not_committed(
            record_id, "the node is on a different chain from the bundle's", root=root
        )

    final = chain.commit_of(bytes.fromhex(root), finalized=True)
    if final is None:
        if chain.commit_of(bytes.fromhex(root)) is not None:
            return VerifyResult(
                "pending", record_id, "the root is on the chain but not yet finalized", root=root
            )
        return _not_committed(record_id, "the chain has no such root", root=root)

    _bar_ts, block_time, _committer = final
    evidence = chain.committed_event(bytes.fromhex(root))
    bar_close_s = (
        bar_close_from_record_bytes(bytes.fromhex(str(record["record_bytes"]))) // SECOND_NS
    )
    return VerifyResult(
        "committed",
        record_id,
        NO_LATER,
        root=root,
        block_number=evidence.block_number if evidence else -1,
        block_time=block_time,
        tx_hash=evidence.tx_hash if evidence else "",
        latency_s=block_time - bar_close_s,
    )


def verify_record(
    catalog: Catalog, chain: NotaryChain, record_id: str, *, contract: str = ""
) -> VerifyResult:
    record = next(
        (
            r
            for r in tables.records_table(catalog).read().to_pylist()
            if r["record_id"] == record_id
        ),
        None,
    )
    if record is None:
        return _not_committed(record_id, "no such record is registered")
    if record["notarizable"] != "yes":
        return _not_committed(record_id, f"unnotarizable: {record['reason']}")

    leaf = next(
        (x for x in tables.leaves_table(catalog).read().to_pylist() if x["record_id"] == record_id),
        None,
    )
    if leaf is None:
        return VerifyResult("pending", record_id, "registered, not yet in a batch")
    state = {str(b["batch_root"]): s for b, s in outbox_states(catalog)}.get(
        str(leaf["batch_root"])
    )
    if state is None or state["event"] != "confirmed":
        event = "formed" if state is None else state["event"]
        why = "" if state is None or not state["detail"] else f": {state['detail']}"
        return VerifyResult(
            "pending", record_id, f"its batch is {event}{why}", root=str(leaf["batch_root"])
        )

    bundle = export_bundle(
        catalog, record_id, chain_id=chain.chain_id(), contract=contract, rpc_hint=""
    )
    return verify_bundle(bundle, chain)


# ---- the commands ------------------------------------------------------------------------------

DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz"
#: Exit codes: a script can tell "not there" from "not yet".
EXIT_COMMITTED, EXIT_NOT_COMMITTED, EXIT_PENDING = 0, 1, 2


def read_only_chain(
    rpc_url: str, *, chain_id: int, contract: str, deploy_block: int
) -> JsonRpcChain:
    """A chain to read from. It never signs, so its account is a throwaway nobody holds."""
    from eth_account import Account

    return JsonRpcChain(
        http_transport(rpc_url),
        chain_id=chain_id,
        contract=contract,
        account=Account.create(),
        gas_margin=1.0,
        from_block=deploy_block,
    )


def _report(result: VerifyResult) -> int:
    print(f"{result.status}: {result.record_id}")
    if result.status == "committed":
        print(
            f"  block {result.block_number}, time {result.block_time}, tx {result.tx_hash}\n"
            f"  bar close to block: {result.latency_s} s\n  root {result.root}"
        )
    elif result.root:
        print(f"  root {result.root}")
    print(f"  {result.detail}")
    return {"committed": EXIT_COMMITTED, "pending": EXIT_PENDING}.get(
        result.status, EXIT_NOT_COMMITTED
    )


def main(
    argv: list[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    catalog: Catalog | None = None,
    chain: NotaryChain | None = None,
) -> int:
    """`check <record_id>`, `export <record_id>`, `bundle <file>`."""
    environment = os.environ if env is None else env
    parser = argparse.ArgumentParser(description="Check a record against the chain.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="verify a record in this lakehouse").add_argument("record_id")
    commands.add_parser("export", help="write a bundle anyone can verify").add_argument("record_id")
    commands.add_parser(
        "bundle", help="verify a bundle: needs only the file and a node"
    ).add_argument("file", type=Path)
    args = parser.parse_args(argv)

    rpc_url = environment.get("MONAD_RPC_URL", "").strip() or DEFAULT_RPC_URL
    chain_id = int(environment.get("MONAD_CHAIN_ID", "").strip() or 10143)
    contract = environment.get("MONAD_NOTARY_ADDRESS", "").strip()
    deploy_block = int(environment.get("MONAD_NOTARY_DEPLOY_BLOCK", "").strip() or 0)

    if args.command == "bundle":
        bundle = json.loads(args.file.read_text())
        where = bundle["chain"]
        node = chain or read_only_chain(
            rpc_url if environment.get("MONAD_RPC_URL") else where.get("rpc_hint") or rpc_url,
            chain_id=int(where["chain_id"]),
            contract=str(where["contract"]),
            deploy_block=int(where.get("deploy_block", 0)),
        )
        return _report(verify_bundle(bundle, node))

    if not contract:
        print("MONAD_NOTARY_ADDRESS must be set", file=sys.stderr)
        return EXIT_NOT_COMMITTED
    if catalog is None:
        settings = settings_from_env(environment)
        catalog = open_catalog(
            uri=settings.catalog_uri, warehouse=settings.warehouse, **dict(settings.storage)
        )
    node = chain or read_only_chain(
        rpc_url, chain_id=chain_id, contract=contract, deploy_block=deploy_block
    )
    if args.command == "export":
        bundle = export_bundle(
            catalog,
            args.record_id,
            chain_id=chain_id,
            contract=contract,
            rpc_hint=rpc_url,
            deploy_block=deploy_block,
        )
        print(json.dumps(bundle, indent=2))
        return EXIT_COMMITTED
    return _report(verify_record(catalog, node, args.record_id, contract=contract))


if __name__ == "__main__":
    raise SystemExit(main())
