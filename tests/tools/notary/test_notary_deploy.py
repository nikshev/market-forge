# @trace: REQ-INFRA-006
"""Deploy, verify and smoke against a chain that can be made to lie (FR-011, FR-012, FR-013)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.tools.notary.conftest import (
    ADDRESS,
    CODE_HASH,
    OWNER,
    TX,
    FakeChain,
    FakeRepo,
    make_config,
)
from tools.notary.deploy import DeployError, deploy
from tools.notary.smoke import SmokeError, smoke
from tools.notary.verify import VerifyError, verify

FIELDS = {
    "chain_id", "address", "tx_hash", "block_number", "block_time", "owner", "deployer",
    "source_commit", "solc", "deployed_code_hash",
}  # fmt: skip


def _deploy(chain: FakeChain, repo: FakeRepo, path: Path, *, broadcast: bool = True) -> dict | None:
    return deploy(
        chain,
        make_config(),
        repo,
        broadcast=broadcast,
        record_path=path,
        out=lambda _: None,
        sleep=lambda _: None,
    )


@pytest.mark.trace("REQ-INFRA-006")
def test_a_dry_run_sends_nothing_and_writes_no_record(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    printed: list[str] = []
    result = deploy(
        chain,
        make_config(),
        repo,
        broadcast=False,
        record_path=record_path,
        out=printed.append,
        sleep=lambda _: None,
    )

    assert result is None
    assert chain.sent == 0 and "create" not in chain.calls
    assert not record_path.exists()
    text = "\n".join(printed)
    assert OWNER in text and "10143" in text and "5" in text  # deployer, chain id, balance


@pytest.mark.trace("REQ-INFRA-006")
def test_a_clean_read_back_writes_the_record_with_every_field(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    record = _deploy(chain, repo, record_path)

    assert record is not None
    written = json.loads(record_path.read_text())
    assert FIELDS <= set(written)
    assert written["address"] == ADDRESS and written["tx_hash"] == TX
    assert written["owner"] == OWNER and written["deployed_code_hash"] == CODE_HASH
    assert written["source_commit"] == repo.commit and written["chain_id"] == 10143
    assert written["block_time"] == chain.block_ts and written["block_number"] == chain.block_number


@pytest.mark.trace("REQ-INFRA-006")
def test_the_owner_is_configuration_and_defaults_to_the_signer(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    other = "0x" + "0e" * 20
    chain.deployed_owner = other
    record = deploy(
        chain,
        make_config(owner=other),
        repo,
        broadcast=True,
        record_path=record_path,
        out=lambda _: None,
        sleep=lambda _: None,
    )
    assert record is not None and record["owner"] == other and record["deployer"] == OWNER


@pytest.mark.trace("REQ-INFRA-006")
@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ({"receipt_status": 0}, "status"),
        ({"receipt_address": "0x" + "88" * 20}, "address"),
        ({"deployed_code_hash": "0x" + "00" * 32}, "code"),
        ({"deployed_owner": "0x" + "07" * 20}, "owner"),
        ({"receipt_sender": "0x" + "05" * 20}, "sender"),
    ],
)
def test_a_failed_read_back_leaves_no_record(
    chain: FakeChain, repo: FakeRepo, record_path: Path, damage: dict, message: str
) -> None:
    for key, value in damage.items():
        setattr(chain, key, value)

    with pytest.raises(DeployError, match=message):
        _deploy(chain, repo, record_path)

    assert not record_path.exists(), "a record was written although the read-back failed"


@pytest.mark.trace("REQ-INFRA-006")
def test_the_wrong_chain_is_refused_before_anything_is_sent(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    chain.chain = 1
    with pytest.raises(Exception, match="10143"):
        _deploy(chain, repo, record_path)
    assert chain.sent == 0 and not record_path.exists()


@pytest.mark.trace("REQ-INFRA-006")
def test_a_dirty_contracts_tree_refuses_to_broadcast_but_not_to_dry_run(
    chain: FakeChain, record_path: Path
) -> None:
    dirty = FakeRepo(clean=False)
    with pytest.raises(DeployError, match="contracts"):
        _deploy(chain, dirty, record_path)
    assert chain.sent == 0 and not record_path.exists()

    assert _deploy(chain, dirty, record_path, broadcast=False) is None


@pytest.mark.trace("REQ-INFRA-006")
def test_a_balance_of_zero_refuses_to_broadcast(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    chain.balance = 0
    with pytest.raises(DeployError, match="balance"):
        _deploy(chain, repo, record_path)
    assert chain.sent == 0


# ---- verify -------------------------------------------------------------------------------------


def _deployed(chain: FakeChain, repo: FakeRepo, path: Path) -> dict:
    record = _deploy(chain, repo, path)
    assert record is not None
    return record


@pytest.mark.trace("REQ-INFRA-006")
def test_verify_passes_for_a_deployment_that_is_what_the_record_says(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    _deployed(chain, repo, record_path)
    verify(chain, make_config(), record_path=record_path, sleep=lambda _: None)


@pytest.mark.trace("REQ-INFRA-006")
@pytest.mark.parametrize(
    ("damage", "message"),
    [
        ({"receipt_status": 0}, "status"),
        ({"receipt_address": "0x" + "88" * 20}, "address"),
        ({"deployed_code_hash": "0x" + "00" * 32}, "code"),
        ({"local_code_hash": "0x" + "01" * 32}, "compiled"),
        ({"deployed_owner": "0x" + "07" * 20}, "owner"),
        ({"chain": 1}, "chain"),
    ],
)
def test_verify_fails_loudly_and_says_which_check_differs(
    chain: FakeChain, repo: FakeRepo, record_path: Path, damage: dict, message: str
) -> None:
    _deployed(chain, repo, record_path)
    for key, value in damage.items():
        setattr(chain, key, value)

    with pytest.raises(VerifyError, match=message):
        verify(chain, make_config(), record_path=record_path, sleep=lambda _: None)


@pytest.mark.trace("REQ-INFRA-006")
def test_verify_reports_a_missing_receipt_as_not_deployed_never_as_success(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    _deployed(chain, repo, record_path)
    chain.receipts_gone = True  # a testnet reset, or a reorganisation: the receipt is gone

    with pytest.raises(VerifyError, match="not deployed|no receipt"):
        verify(chain, make_config(), record_path=record_path, sleep=lambda _: None)


@pytest.mark.trace("REQ-INFRA-006")
def test_verify_without_a_record_says_nothing_was_deployed(
    chain: FakeChain, record_path: Path
) -> None:
    with pytest.raises(VerifyError, match="no deployment record"):
        verify(chain, make_config(), record_path=record_path, sleep=lambda _: None)


# ---- smoke --------------------------------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-006")
def test_smoke_commits_and_resolves_and_records_both_transactions_after_reading_them_back(
    chain: FakeChain, repo: FakeRepo, record_path: Path
) -> None:
    _deployed(chain, repo, record_path)

    block = smoke(
        chain,
        make_config(),
        record_path=record_path,
        now=lambda: 1_791_460_000,
        sleep=lambda _: None,
    )

    saved = json.loads(record_path.read_text())["smoke"]
    assert saved == block
    assert saved["commit_tx"] != saved["resolve_tx"] and saved["outcome"] == 1
    assert chain.outcomes[saved["hash"]] == 1
    assert chain.commits[saved["hash"]][0] == 1_791_460_000


@pytest.mark.trace("REQ-INFRA-006")
@pytest.mark.parametrize("knob", ["break_commit_event", "break_commit_read"])
def test_smoke_records_nothing_when_a_read_back_disagrees(
    chain: FakeChain, repo: FakeRepo, record_path: Path, knob: str
) -> None:
    _deployed(chain, repo, record_path)
    setattr(chain, knob, True)

    with pytest.raises(SmokeError):
        smoke(
            chain,
            make_config(),
            record_path=record_path,
            now=lambda: 1_791_460_000,
            sleep=lambda _: None,
        )

    assert "smoke" not in json.loads(record_path.read_text())
