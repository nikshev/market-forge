# @trace: REQ-INFRA-007
"""Anyone can check a record against the chain; the claim is "no later than" (FR-013)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from channelflow.notary import tables
from channelflow.notary.submitter import Submitter, SubmitterConfig
from channelflow.notary.verify import (
    bar_close_from_record_bytes,
    export_bundle,
    verify_bundle,
    verify_record,
)
from tests.notary.conftest import SECOND, FakeNotaryChain
from tests.notary.test_notary_pass import NOTARY, plane, run

CONTRACT = "0x4a0963b8B35311411Bf17497F0CAeD20d5596682"
WINDOW = 30 * 60 * SECOND


def notarized(tmp_path: Path, *, confirm: bool = True):  # type: ignore[no-untyped-def]
    """A real pass, its records batched and (optionally) sent to a fake chain."""
    catalog = plane(tmp_path / "plane")
    run(catalog, notary=NOTARY)
    records = tables.records_table(catalog).read().to_pylist()
    latest_close = max(int(r["bar_close_time_ns"]) for r in records) // SECOND
    chain = FakeNotaryChain(
        block_ts=latest_close + 2400
    )  # committed ~40 minutes after the last bar
    clock = [max(int(r["registered_at_ns"]) for r in records) + WINDOW]
    submitter = Submitter(
        catalog=catalog,
        chain=chain,
        config=SubmitterConfig(
            window_ns=WINDOW,
            max_batch=10_000,
            min_balance_wei=10**17,
            max_gas_price_wei=500 * 10**9,
            submit_timeout_ns=120 * SECOND,
        ),
        now_ns=lambda: clock[0],
    )
    if confirm:
        submitter.tick()
    return catalog, chain, records, submitter


def pick(records: list[dict[str, object]], kind: str) -> str:
    return str(next(r["record_id"] for r in records if r["kind"] == kind))


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize("kind", ["snapshot", "decision"])
def test_a_notarized_record_verifies_with_its_block_its_transaction_and_its_latency(
    tmp_path: Path, kind: str
) -> None:
    catalog, chain, records, _ = notarized(tmp_path)
    record_id = pick(records, kind)
    row = next(r for r in records if r["record_id"] == record_id)

    result = verify_record(catalog, chain, record_id)

    assert result.status == "committed"
    assert result.block_time == chain.block_ts and result.block_number == chain.block_number
    assert result.tx_hash.startswith("0x")
    assert result.latency_s == chain.block_ts - int(row["bar_close_time_ns"]) // SECOND  # type: ignore[call-overload]
    assert "no later than" in result.detail and "before" not in result.detail.replace(
        "no later than", ""
    )


@pytest.mark.trace("REQ-INFRA-007")
def test_the_bar_close_is_read_from_the_records_own_bytes(tmp_path: Path) -> None:
    _, _, records, _ = notarized(tmp_path)
    for kind in ("snapshot", "decision"):
        row = next(r for r in records if r["kind"] == kind)
        assert bar_close_from_record_bytes(bytes.fromhex(str(row["record_bytes"]))) == int(
            row["bar_close_time_ns"]  # type: ignore[call-overload]
        )


@pytest.mark.trace("REQ-INFRA-007")
def test_a_bundle_verifies_with_nothing_but_the_bundle_and_the_chain(tmp_path: Path) -> None:
    catalog, chain, records, _ = notarized(tmp_path)
    bundle = export_bundle(
        catalog,
        pick(records, "snapshot"),
        chain_id=10143,
        contract=CONTRACT,
        rpc_hint="https://rpc.example",
    )
    wire = json.loads(json.dumps(bundle))  # what a third party actually receives

    result = verify_bundle(wire, chain)  # no catalog anywhere

    assert result.status == "committed"
    assert wire["chain"]["contract"] == CONTRACT and wire["scheme_version"] == 1


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(
    ("edit", "why"),
    [
        (
            lambda b: b["record"].update(record_bytes=b["record"]["record_bytes"][:-2] + "00"),
            "hash",
        ),
        (lambda b: b["context"].update(config_hash="f" * 64), "hash"),
        (lambda b: b["context"].update(dataset_ref="f" * 64), "hash"),
        (lambda b: b["context"].update(code_commit="f" * 40), "hash"),
        (lambda b: b["inclusion"]["path"].__setitem__(0, "00" * 32), "inclusion"),
        (lambda b: b["inclusion"].update(leaf_index=b["inclusion"]["leaf_index"] + 1), "inclusion"),
        (lambda b: b.update(root="00" * 32), "inclusion"),
    ],
    ids=["record", "config", "dataset", "commit", "path", "index", "root"],
)
def test_any_altered_field_is_not_committed_and_says_why(tmp_path: Path, edit, why: str) -> None:  # type: ignore[no-untyped-def]
    catalog, chain, records, _ = notarized(tmp_path)
    bundle = export_bundle(
        catalog, pick(records, "snapshot"), chain_id=10143, contract=CONTRACT, rpc_hint=""
    )
    tampered = copy.deepcopy(json.loads(json.dumps(bundle)))
    # Make the claim as good as it can be: a path of one is only altered if it has a first element.
    if why == "inclusion" and not tampered["inclusion"]["path"]:
        tampered["inclusion"]["tree_size"] += 1
    else:
        edit(tampered)

    result = verify_bundle(tampered, chain)

    assert result.status == "not committed" and why in result.detail


@pytest.mark.trace("REQ-INFRA-007")
def test_a_root_the_chain_does_not_have_is_not_committed(tmp_path: Path) -> None:
    catalog, chain, records, _ = notarized(tmp_path)
    bundle = export_bundle(
        catalog, pick(records, "snapshot"), chain_id=10143, contract=CONTRACT, rpc_hint=""
    )
    chain.commits.clear()  # the chain, asked independently, has nothing

    result = verify_bundle(json.loads(json.dumps(bundle)), chain)

    assert result.status == "not committed" and "chain" in result.detail


@pytest.mark.trace("REQ-INFRA-007")
def test_a_record_in_an_unconfirmed_batch_is_pending_never_committed(tmp_path: Path) -> None:
    catalog, chain, records, submitter = notarized(tmp_path, confirm=False)
    chain.down = True
    submitter.tick()  # batches form; nothing reaches the chain

    result = verify_record(catalog, chain, pick(records, "snapshot"))

    assert result.status == "pending" and "batch" in result.detail


@pytest.mark.trace("REQ-INFRA-007")
def test_a_record_not_yet_in_any_batch_is_pending(tmp_path: Path) -> None:
    catalog, chain, records, _ = notarized(
        tmp_path, confirm=False
    )  # registered, window not elapsed

    result = verify_record(catalog, chain, pick(records, "snapshot"))

    assert result.status == "pending" and "not yet in a batch" in result.detail


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unknown_record_and_an_unnotarizable_one_are_not_committed(tmp_path: Path) -> None:
    catalog, chain, records, _ = notarized(tmp_path)
    assert verify_record(catalog, chain, "snapshot|nobody|X|1|1").status == "not committed"

    unnotarizable = plane(tmp_path / "second")
    from channelflow.notary.config import WorkerNotary

    run(unnotarizable, notary=WorkerNotary(from_ns=0, code_commit=None, code_dirty=None))
    row = tables.records_table(unnotarizable).read().to_pylist()[0]
    result = verify_record(unnotarizable, chain, str(row["record_id"]))
    assert result.status == "not committed" and "unnotarizable" in result.detail
