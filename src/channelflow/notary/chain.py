"""The notary's face on the chain: a port, and its JSON-RPC implementation (REQ-INFRA-007).

# @trace: REQ-INFRA-007

The submitter talks to `NotaryChain` and nothing else, so everything it has to survive -- an
unreachable node, a process that dies between sending and recording, a root that is visible but
not yet finalized, an empty wallet -- can be made to happen in a test with an in-memory chain.

`JsonRpcChain` is that port over nine JSON-RPC calls and one signature; `eth-account` signs, `httpx`
carries. **Nothing secret reaches a message.** The key lives in the `LocalAccount` and is never
formatted; the keystore password is read, used and dropped; and an RPC URL is reduced to its host
in every error, because a provider's API key is usually its path or its query string.

**Monad charges the gas limit, not the gas used** (measured: research R4). So the limit is the
estimate times a small configured margin and nothing more; every unit of slack is paid for.
"""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlsplit

import httpx
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_hash.auto import keccak
from eth_utils.address import to_checksum_address


class ChainDown(RuntimeError):
    """The node could not be reached, or refused a call. Retried on the next tick."""


class WrongChain(RuntimeError):
    """The node reports a different chain id from the one configured."""


class NotOwner(RuntimeError):
    """The signing account is not the contract's `owner()`; every commit it sent would revert."""


@dataclass(frozen=True)
class Receipt:
    status: int
    block_number: int


@dataclass(frozen=True)
class SentTx:
    tx_hash: str
    nonce: int


@dataclass(frozen=True)
class CommitEvidence:
    """Where the chain says a root was committed, recovered from its `Committed` log."""

    tx_hash: str
    block_number: int
    block_time: int  # seconds, assigned by the chain


class NotaryChain(Protocol):
    def chain_id(self) -> int: ...
    def signer_address(self) -> str: ...
    def balance_wei(self) -> int: ...
    def gas_price_wei(self) -> int: ...
    def commit_of(self, root: bytes, *, finalized: bool = False) -> tuple[int, int, str] | None:
        """`(barTs, blockTime, committer)` if the root is committed, else `None`."""
        ...

    def committed_event(self, root: bytes) -> CommitEvidence | None: ...
    def send_commit(self, root: bytes, bar_ts: int) -> SentTx: ...
    def receipt(self, tx_hash: str) -> Receipt | None: ...
    def block_time(self, number: int) -> int: ...


# ---- the JSON-RPC implementation ---------------------------------------------------------------

Transport = Callable[[str, list[Any]], Any]


def _selector(signature: str) -> str:
    return "0x" + keccak(signature.encode())[:4].hex()


COMMIT_SELECTOR = _selector("commit(bytes32,uint64)")
COMMIT_OF_SELECTOR = _selector("commitOf(bytes32)")
OWNER_SELECTOR = _selector("owner()")
COMMITTED_TOPIC = "0x" + keccak(b"Committed(bytes32,uint64,address)").hex()
_ZERO_ADDRESS = "0x" + "00" * 20


def redact(url: str) -> str:
    """Scheme, host and port only. A provider's API key is often the path or the query."""
    parts = urlsplit(url)
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname}{port}"


def _scrub(text: str, url: str) -> str:
    """Remove from a message about `url` anything that could be a credential in it."""
    parts = urlsplit(url)
    secrets = {parts.username or "", parts.password or ""}
    secrets |= {segment for segment in parts.path.split("/") if len(segment) > 3}
    secrets |= {value for _key, value in parse_qsl(parts.query)}
    text = text.replace(url, redact(url))
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        text = text.replace(secret, "***")
    return text


def http_transport(
    url: str, *, client: httpx.Client | None = None, timeout: float = 20.0
) -> Transport:
    """JSON-RPC over HTTP. Every failure is a `ChainDown` that names the host and nothing more."""
    http = client or httpx.Client(timeout=timeout)
    ids = itertools.count(1)
    host = redact(url)

    def send(method: str, params: list[Any]) -> Any:
        body = {"jsonrpc": "2.0", "id": next(ids), "method": method, "params": params}
        try:
            response = http.post(url, json=body)
        except httpx.HTTPError as error:
            raise ChainDown(f"{host}: {type(error).__name__}: {_scrub(str(error), url)}") from None
        if response.status_code >= 400:
            raise ChainDown(f"{host}: HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError:
            raise ChainDown(f"{host}: the reply is not JSON") from None
        if isinstance(payload, dict) and payload.get("error"):
            reported = payload["error"]
            message = reported.get("message", "error") if isinstance(reported, dict) else reported
            raise ChainDown(f"{host}: {method}: {message}")
        if not isinstance(payload, dict) or "result" not in payload:
            raise ChainDown(f"{host}: the reply has no result")
        return payload["result"]

    return send


def load_signer(keystore: Path, password_file: Path) -> LocalAccount:
    """Open a Foundry keystore. Neither the password nor the key appears in any message."""
    password = password_file.read_text().strip()
    document = json.loads(keystore.read_text())
    try:
        key = Account.decrypt(document, password)
    except ValueError:
        raise ValueError(
            f"the keystore {keystore.name} could not be decrypted with the password in "
            f"{password_file.name}"
        ) from None
    account: LocalAccount = Account.from_key(key)
    return account


def _int(value: Any) -> int:
    return int(str(value), 16)


class JsonRpcChain:
    """`NotaryChain` over JSON-RPC, signing with a local account."""

    def __init__(
        self,
        transport: Transport,
        *,
        chain_id: int,
        contract: str,
        account: LocalAccount,
        gas_margin: float,
        from_block: int,
    ) -> None:
        self.transport = transport
        self._chain_id = chain_id
        self._contract = contract
        self._account = account
        self._gas_margin = gas_margin
        self._from_block = from_block

    def __repr__(self) -> str:
        return f"JsonRpcChain(contract={self._contract}, signer={self._account.address})"

    def _call(self, method: str, *params: Any) -> Any:
        return self.transport(method, list(params))

    # ---- start-up check -------------------------------------------------------------------------

    def verify_ready(self) -> None:
        """Refuse to run on the wrong chain or with a signer the contract would reject."""
        actual = self.chain_id()
        if actual != self._chain_id:
            raise WrongChain(
                f"configured chain id is {self._chain_id} but the node reports {actual}"
            )
        owner = "0x" + self._eth_call(OWNER_SELECTOR, "latest").removeprefix("0x")[-40:]
        if owner.lower() != str(self._account.address).lower():
            raise NotOwner(
                f"the signing address {self._account.address} is not the contract's owner {owner}"
            )

    # ---- reads ----------------------------------------------------------------------------------

    def chain_id(self) -> int:
        return _int(self._call("eth_chainId"))

    def signer_address(self) -> str:
        return str(self._account.address)

    def balance_wei(self) -> int:
        return _int(self._call("eth_getBalance", self._account.address, "latest"))

    def gas_price_wei(self) -> int:
        return _int(self._call("eth_gasPrice"))

    def _eth_call(self, data: str, tag: str) -> str:
        result = str(self._call("eth_call", {"to": self._contract, "data": data}, tag))
        if result in ("0x", ""):
            raise ChainDown("the contract returned nothing: is the address a SignalNotary?")
        return result

    def commit_of(self, root: bytes, *, finalized: bool = False) -> tuple[int, int, str] | None:
        words = self._eth_call(
            COMMIT_OF_SELECTOR + root.hex(), "finalized" if finalized else "latest"
        ).removeprefix("0x")
        committer = "0x" + words[152:192]
        if committer == _ZERO_ADDRESS:
            return None
        return int(words[0:64], 16), int(words[64:128], 16), to_checksum_address(committer)

    def committed_event(self, root: bytes) -> CommitEvidence | None:
        logs = self._call(
            "eth_getLogs",
            {
                "address": self._contract,
                "fromBlock": hex(self._from_block),
                "toBlock": "latest",
                "topics": [COMMITTED_TOPIC, "0x" + root.hex()],
            },
        )
        if not logs:
            return None
        log = logs[0]
        number = _int(log["blockNumber"])
        return CommitEvidence(
            tx_hash=str(log["transactionHash"]),
            block_number=number,
            block_time=self.block_time(number),
        )

    def receipt(self, tx_hash: str) -> Receipt | None:
        raw = self._call("eth_getTransactionReceipt", tx_hash)
        if raw is None:
            return None
        return Receipt(status=_int(raw["status"]), block_number=_int(raw["blockNumber"]))

    def block_time(self, number: int) -> int:
        return _int(self._call("eth_getBlockByNumber", hex(number), False)["timestamp"])

    # ---- the one write --------------------------------------------------------------------------

    def send_commit(self, root: bytes, bar_ts: int) -> SentTx:
        data = COMMIT_SELECTOR + root.hex() + format(bar_ts, "064x")
        call = {"from": self._account.address, "to": self._contract, "data": data}
        estimate = _int(self._call("eth_estimateGas", call))
        nonce = _int(self._call("eth_getTransactionCount", self._account.address, "pending"))
        transaction: dict[str, Any] = {
            "chainId": self._chain_id,
            "nonce": nonce,
            "gasPrice": _int(self._call("eth_gasPrice")),
            # Monad bills the limit: the estimate and a configured margin, nothing more.
            "gas": int(estimate * self._gas_margin),
            "to": self._contract,
            "value": 0,
            "data": data,
        }
        signed = self._account.sign_transaction(transaction)
        raw = "0x" + bytes(signed.raw_transaction).hex()
        return SentTx(tx_hash=str(self._call("eth_sendRawTransaction", raw)), nonce=nonce)
