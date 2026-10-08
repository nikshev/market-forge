# @trace: REQ-INFRA-006
"""A chain and a repository that can be made to lie, for the notary tool tests.

`FakeChain` implements the same port as `tools.notary.chain.Chain` but keeps everything in memory
and records every call, so a test can assert both what the tool concluded and what it asked the
chain to do. Each `break_*` attribute damages exactly one thing the read-back is supposed to catch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tools.notary.chain import Config, Log, Receipt

OWNER = "0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131"
ADDRESS = "0x9999999999999999999999999999999999999999"
TX = "0x" + "11" * 32
CODE_HASH = "0x" + "c0" * 32
COMMITTED_TOPIC = "0x" + "e1" * 32
RESOLVED_TOPIC = "0x" + "e2" * 32


def make_config(**changes: object) -> Config:
    base: dict[str, object] = {
        "rpc_url": "https://rpc.example",
        "chain_id": 10143,
        "explorer_url": "https://explorer.example",
        "account": "notary-deployer",
        "password_file": Path("/nonexistent/keystore.pass"),
        "owner": None,
    }
    base.update(changes)
    return Config(**base)  # type: ignore[arg-type]


@dataclass
class FakeChain:
    chain: int = 10143
    signer: str = OWNER
    balance: int = 5 * 10**18
    local_code_hash: str = CODE_HASH
    # what the "network" holds
    deployed_code_hash: str = CODE_HASH
    deployed_owner: str = OWNER
    receipt_status: int = 1
    receipt_address: str = ADDRESS
    receipt_sender: str = OWNER
    block_number: int = 69_200_000
    block_ts: int = 1_791_450_000
    # recorded behaviour
    calls: list[str] = field(default_factory=list)
    commits: dict[str, tuple[int, int, str]] = field(default_factory=dict)
    outcomes: dict[str, int] = field(default_factory=dict)
    receipts: dict[str, Receipt] = field(default_factory=dict)
    sent: int = 0
    # knobs
    break_commit_event: bool = False
    break_commit_read: bool = False
    receipts_gone: bool = False

    # ---- the port ---------------------------------------------------------------------------
    def chain_id(self) -> int:
        self.calls.append("chain_id")
        return self.chain

    def signer_address(self) -> str:
        self.calls.append("signer_address")
        return self.signer

    def balance_wei(self, address: str) -> int:
        self.calls.append("balance_wei")
        return self.balance

    def expected_code_hash(self) -> str:
        self.calls.append("expected_code_hash")
        return self.local_code_hash

    def keccak(self, text: str) -> str:
        self.calls.append("keccak")
        return {
            "Committed(bytes32,uint64,address)": COMMITTED_TOPIC,
            "Resolved(bytes32,uint8)": RESOLVED_TOPIC,
        }.get(text, "0x" + format(abs(hash(text)) % (1 << 256), "064x"))

    def create(self, owner: str) -> tuple[str, str]:
        self.calls.append("create")
        self.sent += 1
        return TX, ADDRESS

    def receipt(self, tx_hash: str) -> Receipt | None:
        self.calls.append("receipt")
        if tx_hash == TX:
            # The deployment receipt is read from the attributes each time, so a test can damage
            # what the "network" holds after the deployment was recorded.
            if self.sent == 0 or self.receipts_gone:
                return None
            return Receipt(
                status=self.receipt_status,
                contract_address=self.receipt_address,
                block_number=self.block_number,
                sender=self.receipt_sender,
                logs=(),
            )
        return self.receipts.get(tx_hash)

    def code_hash(self, address: str) -> str:
        self.calls.append("code_hash")
        return self.deployed_code_hash

    def owner_of(self, address: str) -> str:
        self.calls.append("owner_of")
        return self.deployed_owner

    def block_time(self, number: int) -> int:
        self.calls.append("block_time")
        return self.block_ts

    def send(self, address: str, signature: str, args: tuple[str, ...]) -> str:
        self.calls.append(f"send:{signature}")
        self.sent += 1
        tx = "0x" + format(0x2000 + self.sent, "064x")
        name = signature.split("(")[0]
        topic = COMMITTED_TOPIC if name == "commit" else RESOLVED_TOPIC
        if name == "commit":
            key = args[0]
            self.commits[key] = (int(args[1]), self.block_ts, self.signer)
            if self.break_commit_read:
                self.commits[key] = (int(args[1]) + 1, self.block_ts, self.signer)
            logs = () if self.break_commit_event else (Log(topics=(topic, key)),)
        else:
            self.outcomes[args[0]] = int(args[1])
            logs = (Log(topics=(topic, args[0])),)
        self.receipts[tx] = Receipt(
            status=1,
            contract_address=None,
            block_number=self.block_number + self.sent,
            sender=self.signer,
            logs=logs,
        )
        return tx

    def commit_of(self, address: str, hash_: str) -> tuple[int, int, str]:
        self.calls.append("commit_of")
        return self.commits.get(hash_, (0, 0, "0x" + "00" * 20))

    def outcome_of(self, address: str, hash_: str) -> int:
        self.calls.append("outcome_of")
        return self.outcomes.get(hash_, 0)


@dataclass
class FakeRepo:
    clean: bool = True
    commit: str = "a" * 40

    def contracts_clean(self) -> bool:
        return self.clean

    def head(self) -> str:
        return self.commit


@pytest.fixture
def chain() -> FakeChain:
    return FakeChain()


@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


@pytest.fixture
def record_path(tmp_path: Path) -> Path:
    return tmp_path / "deployments" / "monad-testnet.json"
