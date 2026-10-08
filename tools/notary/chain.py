# @trace: REQ-INFRA-006
"""A thin, typed face over `cast` and `forge` for the SignalNotary tools (REQ-INFRA-006).

Every command line the tools send is assembled here, so there is one place to look for a secret in
an argument list. There is none to find: signing is `--account <name> --password-file <path>`, a
Foundry keystore whose password sits in a file outside the repository. The configuration has no
field that could hold a key, and a key in the environment is never read.

Nothing here decides what a deployment *means*; `deploy.py`, `verify.py` and `smoke.py` do that
against the `ChainPort` below, which a test replaces with an in-memory fake.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

DEFAULT_RPC_URL = "https://testnet-rpc.monad.xyz"
DEFAULT_CHAIN_ID = 10143
DEFAULT_EXPLORER_URL = "https://testnet.monadvision.com"
CONTRACT = "src/SignalNotary.sol:SignalNotary"
ZERO_ADDRESS = "0x" + "00" * 20
NO_CODE = "none"


class ConfigError(ValueError):
    """A required variable is missing or malformed; the message names it."""


class ChainError(RuntimeError):
    """A `cast`/`forge` command failed."""


class ChainMismatch(ChainError):
    """The node reports a different chain id from the configured one."""


@dataclass(frozen=True)
class Config:
    rpc_url: str
    chain_id: int
    explorer_url: str
    account: str
    password_file: Path
    owner: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Config:
        """Read the network and the signer from the environment (Principle X).

        The signer is a keystore *account name* and a *password file path*. No variable that could
        hold a private key is consulted, whatever else is in the environment.
        """

        def required(name: str) -> str:
            value = env.get(name, "").strip()
            if not value:
                raise ConfigError(f"{name} is not set")
            return value

        try:
            chain_id = int(env.get("MONAD_CHAIN_ID", "") or DEFAULT_CHAIN_ID)
        except ValueError as error:
            raise ConfigError(f"MONAD_CHAIN_ID is not an integer: {error}") from error
        return cls(
            rpc_url=env.get("MONAD_RPC_URL", "").strip() or DEFAULT_RPC_URL,
            chain_id=chain_id,
            explorer_url=env.get("MONAD_EXPLORER_URL", "").strip() or DEFAULT_EXPLORER_URL,
            account=required("MONAD_SIGNER_ACCOUNT"),
            password_file=Path(required("MONAD_SIGNER_PASSWORD_FILE")),
            owner=env.get("MONAD_NOTARY_OWNER", "").strip() or None,
        )


@dataclass(frozen=True)
class Log:
    topics: tuple[str, ...]


@dataclass(frozen=True)
class Receipt:
    status: int
    contract_address: str | None
    block_number: int
    sender: str
    logs: tuple[Log, ...]


class ChainPort(Protocol):
    """What the tools need from a chain. `Chain` implements it; tests implement it in memory."""

    def chain_id(self) -> int: ...
    def signer_address(self) -> str: ...
    def balance_wei(self, address: str) -> int: ...
    def expected_code_hash(self) -> str: ...
    def keccak(self, text: str) -> str: ...
    def create(self, owner: str) -> tuple[str, str]: ...
    def receipt(self, tx_hash: str) -> Receipt | None: ...
    def code_hash(self, address: str) -> str: ...
    def owner_of(self, address: str) -> str: ...
    def block_time(self, number: int) -> int: ...
    def send(self, address: str, signature: str, args: tuple[str, ...]) -> str: ...
    def commit_of(self, address: str, hash_: str) -> tuple[int, int, str]: ...
    def outcome_of(self, address: str, hash_: str) -> int: ...


Runner = Callable[[Sequence[str], Path | None], str]


def subprocess_runner(argv: Sequence[str], cwd: Path | None) -> str:
    """Run a command, return stdout, raise `ChainError` with stderr on a non-zero exit."""
    proc = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0:
        raise ChainError(f"{' '.join(argv[:2])} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def signing_flags(config: Config) -> list[str]:
    """How a command signs: a keystore account and its password file. Never a key."""
    return ["--account", config.account, "--password-file", str(config.password_file)]


def _hex_int(value: object) -> int:
    return int(str(value), 16) if str(value).startswith("0x") else int(str(value))


class Chain:
    def __init__(self, config: Config, *, runner: Runner, contracts_dir: Path) -> None:
        self.config = config
        self._run = runner
        self._contracts = contracts_dir

    # ---- reads -------------------------------------------------------------------------------

    def _cast(self, *args: str) -> str:
        return self._run(["cast", *args], None).strip()

    def chain_id(self) -> int:
        return int(self._cast("chain-id", "--rpc-url", self.config.rpc_url))

    def ensure_expected_chain(self) -> None:
        actual = self.chain_id()
        if actual != self.config.chain_id:
            raise ChainMismatch(
                f"configured chain id is {self.config.chain_id} but the node at "
                f"{self.config.rpc_url} reports {actual}"
            )

    def signer_address(self) -> str:
        return self._cast(
            "wallet",
            "address",
            "--account",
            self.config.account,
            "--password-file",
            str(self.config.password_file),
        )

    def balance_wei(self, address: str) -> int:
        return int(self._cast("balance", address, "--rpc-url", self.config.rpc_url))

    def keccak(self, text: str) -> str:
        return self._cast("keccak", text)

    def expected_code_hash(self) -> str:
        code = self._run(["forge", "inspect", "SignalNotary", "deployedBytecode"], self._contracts)
        return self.keccak(code.strip())

    def receipt(self, tx_hash: str) -> Receipt | None:
        try:
            raw = self._cast(
                "receipt", tx_hash, "--rpc-url", self.config.rpc_url, "--json", "--async"
            )
        except ChainError as error:
            if "not found" in str(error).lower():
                return None
            raise
        if not raw:
            return None
        return _parse_receipt(json.loads(raw))

    def code_hash(self, address: str) -> str:
        code = self._cast("code", address, "--rpc-url", self.config.rpc_url)
        return NO_CODE if code in ("", "0x") else self.keccak(code)

    def owner_of(self, address: str) -> str:
        return self._cast("call", address, "owner()(address)", "--rpc-url", self.config.rpc_url)

    def block_time(self, number: int) -> int:
        return int(
            self._cast("block", str(number), "--rpc-url", self.config.rpc_url, "-f", "timestamp")
        )

    def commit_of(self, address: str, hash_: str) -> tuple[int, int, str]:
        out = self._cast(
            "call",
            address,
            "commitOf(bytes32)(uint64,uint64,address)",
            hash_,
            "--rpc-url",
            self.config.rpc_url,
        )
        bar_ts, block_time, committer = (line.split()[0] for line in out.splitlines())
        return int(bar_ts), int(block_time), committer

    def outcome_of(self, address: str, hash_: str) -> int:
        out = self._cast(
            "call", address, "outcomeOf(bytes32)(uint8)", hash_, "--rpc-url", self.config.rpc_url
        )
        return int(out.split()[0])

    # ---- writes ------------------------------------------------------------------------------

    def create(self, owner: str) -> tuple[str, str]:
        """Deploy the contract with `owner`; return (transaction hash, created address)."""
        out = self._run(
            [
                "forge",
                "create",
                CONTRACT,
                "--rpc-url",
                self.config.rpc_url,
                *signing_flags(self.config),
                "--broadcast",
                "--json",
                "--constructor-args",
                owner,
            ],
            self._contracts,
        )
        created = json.loads(out)
        return str(created["transactionHash"]), str(created["deployedTo"])

    def send(self, address: str, signature: str, args: tuple[str, ...]) -> str:
        out = self._cast(
            "send",
            address,
            signature,
            *args,
            "--rpc-url",
            self.config.rpc_url,
            *signing_flags(self.config),
            "--json",
        )
        return str(json.loads(out)["transactionHash"])


def _parse_receipt(raw: Mapping[str, object]) -> Receipt:
    raw_logs = raw.get("logs") or []
    logs = tuple(Log(topics=tuple(str(t) for t in log["topics"])) for log in raw_logs)  # type: ignore[attr-defined,union-attr,index]
    contract = raw.get("contractAddress")
    return Receipt(
        status=_hex_int(raw["status"]),
        contract_address=str(contract) if contract else None,
        block_number=_hex_int(raw["blockNumber"]),
        sender=str(raw["from"]),
        logs=logs,
    )
