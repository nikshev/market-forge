# @trace: REQ-INFRA-006
"""The command lines `Chain` builds: configuration, chain id, and the key (FR-010)."""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.tools.notary.conftest import make_config
from tools.notary.chain import Chain, ChainMismatch, Config, ConfigError, signing_flags

KEY = "0x" + "ab" * 32
HEX_64 = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")
FORBIDDEN_FLAGS = {"--private-key", "--mnemonic", "--password", "--interactive", "-i"}


class Recorder:
    """A runner that records every argv and answers like the real tools."""

    def __init__(self, chain_id: str = "10143") -> None:
        self.argvs: list[list[str]] = []
        self.chain_id = chain_id

    def __call__(self, argv: Sequence[str], cwd: Path | None) -> str:
        self.argvs.append(list(argv))
        joined = " ".join(argv)
        if "chain-id" in joined:
            return self.chain_id
        if argv[:3] == ["cast", "wallet", "address"]:
            return "0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131"
        if argv[:2] == ["forge", "create"]:
            return (
                '{"deployer":"0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131","deployedTo":"0x'
                + "99" * 20
                + '","transactionHash":"0x'
                + "11" * 32
                + '"}'
            )
        if argv[:2] == ["cast", "send"]:
            return '{"transactionHash":"0x' + "22" * 32 + '","status":"0x1"}'
        return ""


@pytest.mark.trace("REQ-INFRA-006")
def test_a_missing_signer_account_is_an_error_that_names_the_variable() -> None:
    with pytest.raises(ConfigError, match="MONAD_SIGNER_ACCOUNT"):
        Config.from_env({"MONAD_SIGNER_PASSWORD_FILE": "/x"})
    with pytest.raises(ConfigError, match="MONAD_SIGNER_PASSWORD_FILE"):
        Config.from_env({"MONAD_SIGNER_ACCOUNT": "a"})


@pytest.mark.trace("REQ-INFRA-006")
def test_the_network_comes_from_the_environment_with_the_published_testnet_as_default() -> None:
    env = {"MONAD_SIGNER_ACCOUNT": "a", "MONAD_SIGNER_PASSWORD_FILE": "/x"}
    default = Config.from_env(env)
    assert (default.chain_id, default.rpc_url) == (10143, "https://testnet-rpc.monad.xyz")
    assert default.explorer_url == "https://testnet.monadvision.com"
    assert default.owner is None

    other = Config.from_env(
        env
        | {
            "MONAD_RPC_URL": "http://127.0.0.1:8545",
            "MONAD_CHAIN_ID": "31337",
            "MONAD_NOTARY_OWNER": "0xabc",
        }
    )
    assert (other.chain_id, other.rpc_url, other.owner) == (31337, "http://127.0.0.1:8545", "0xabc")


@pytest.mark.trace("REQ-INFRA-006")
def test_a_key_in_the_environment_is_never_read_into_the_configuration() -> None:
    env = {
        "MONAD_SIGNER_ACCOUNT": "a",
        "MONAD_SIGNER_PASSWORD_FILE": "/x",
        "MONAD_DEPLOYER_KEY": KEY,
        "ETH_PRIVATE_KEY": KEY,
    }
    config = Config.from_env(env)
    assert KEY not in repr(config)
    assert not [f.name for f in dataclasses.fields(Config) if "key" in f.name.lower()]


@pytest.mark.trace("REQ-INFRA-006")
def test_signing_is_an_account_and_a_password_file_and_nothing_else() -> None:
    flags = signing_flags(make_config(account="notary-deployer", password_file=Path("/p/pass")))
    assert flags == ["--account", "notary-deployer", "--password-file", "/p/pass"]


@pytest.mark.trace("REQ-INFRA-006")
def test_no_command_line_the_chain_builds_carries_a_raw_key() -> None:
    runner = Recorder()
    chain = Chain(make_config(), runner=runner, contracts_dir=Path("/c"))

    chain.signer_address()
    chain.create(owner="0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131")
    chain.send("0x" + "99" * 20, "commit(bytes32,uint64)", ("0x" + "aa" * 32, "940"))

    assert runner.argvs, "the chain ran nothing"
    for argv in runner.argvs:
        assert not FORBIDDEN_FLAGS & set(argv), argv
        assert KEY not in argv
    # A deployment has no 32-byte value to pass; a 64-hex token on its command line would be a key.
    create = next(a for a in runner.argvs if a[:2] == ["forge", "create"])
    assert not [token for token in create if HEX_64.match(token)], create
    # Every signing command names the keystore account.
    for argv in runner.argvs:
        if argv[:2] in (["forge", "create"], ["cast", "send"]):
            assert "--account" in argv and "--password-file" in argv


@pytest.mark.trace("REQ-INFRA-006")
def test_a_chain_id_other_than_the_configured_one_is_refused_before_any_transaction() -> None:
    runner = Recorder(chain_id="1")
    chain = Chain(make_config(chain_id=10143), runner=runner, contracts_dir=Path("/c"))

    with pytest.raises(ChainMismatch, match="10143.*1|1.*10143"):
        chain.ensure_expected_chain()

    assert [a for a in runner.argvs if a[:2] in (["forge", "create"], ["cast", "send"])] == []
