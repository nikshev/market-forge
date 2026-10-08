# @trace: REQ-INFRA-007
"""The JSON-RPC client and the signer (FR-009, FR-015): calldata, signing, reads, no leaks."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import rlp
from eth_account import Account

from channelflow.notary.chain import (
    ChainDown,
    JsonRpcChain,
    NotOwner,
    WrongChain,
    http_transport,
    load_signer,
)

CONTRACT = "0x4a0963b8B35311411Bf17497F0CAeD20d5596682"
ROOT = bytes.fromhex("ab" * 32)
PASSWORD = "correct horse battery staple"
ACCOUNT = Account.create()

# Expected bytes produced by Foundry's `cast`, not by this code:
#   cast calldata "commit(bytes32,uint64)" 0xab..ab 940
COMMIT_CALLDATA = (
    "0x5838d673" + "ab" * 32 + "00000000000000000000000000000000000000000000000000000000000003ac"
)
COMMIT_OF_SELECTOR = "0xd706bb28"  # cast sig "commitOf(bytes32)"
OWNER_SELECTOR = "0x8da5cb5b"  # cast sig "owner()"
COMMITTED_TOPIC = "0x6eb32779e3e930732caf971e03a5065225795eac210326c5ab3e3fe9c79fa271"


def word(value: int) -> str:
    return format(value, "064x")


def addr_word(address: str) -> str:
    return "00" * 12 + address.removeprefix("0x").lower()


class FakeNode:
    """A JSON-RPC server in a dict. Records every call; answers like a Monad node would."""

    def __init__(self, *, chain_id: int = 10143, owner: str | None = None) -> None:
        self.calls: list[tuple[str, list[object]]] = []
        self.chain_id = chain_id
        self.owner = owner or ACCOUNT.address
        self.committed: dict[str, tuple[int, int, str]] = {}
        self.logs: list[dict[str, object]] = []
        self.receipts: dict[str, dict[str, object] | None] = {}
        self.raw: list[str] = []
        self.estimate = 79_455
        self.fail: Exception | None = None
        self.log_ranges: list[tuple[int, int]] = []

    def __call__(self, method: str, params: list[object]) -> object:
        self.calls.append((method, params))
        if self.fail is not None:
            raise self.fail
        handler = getattr(self, "rpc_" + method)
        return handler(*params)

    def rpc_eth_chainId(self) -> str:
        return hex(self.chain_id)

    def rpc_eth_getBalance(self, address: str, tag: str) -> str:
        return hex(5 * 10**18)

    def rpc_eth_gasPrice(self) -> str:
        return hex(103 * 10**9)

    def rpc_eth_getTransactionCount(self, address: str, tag: str) -> str:
        return hex(7)

    def rpc_eth_estimateGas(self, tx: dict[str, object]) -> str:
        return hex(self.estimate)

    def rpc_eth_sendRawTransaction(self, raw: str) -> str:
        self.raw.append(raw)
        return "0x" + "cd" * 32

    def rpc_eth_call(self, tx: dict[str, object], tag: str) -> str:
        data = str(tx["data"])
        if data.startswith(OWNER_SELECTOR):
            return "0x" + addr_word(self.owner)
        if data.startswith(COMMIT_OF_SELECTOR):
            root = data[len(COMMIT_OF_SELECTOR) :]
            bar_ts, block_time, committer = self.committed.get(root, (0, 0, "0x" + "00" * 20))
            return "0x" + word(bar_ts) + word(block_time) + addr_word(committer)
        raise AssertionError(f"unexpected call {data[:10]}")

    #: Blocks arrive three to a second, as on Monad: many blocks share one timestamp.
    BASE_BLOCK = 69_218_030
    BASE_TIME = 1_791_450_000
    HEAD = 69_330_000

    def block_timestamp(self, number: int) -> int:
        return self.BASE_TIME + (number - self.BASE_BLOCK) // 3

    def rpc_eth_blockNumber(self) -> str:
        return hex(self.HEAD)

    def rpc_eth_getLogs(self, query: dict[str, object]) -> list[dict[str, object]]:
        start, end = int(str(query["fromBlock"]), 16), int(str(query["toBlock"]), 16)
        if end - start + 1 > 100:  # what the public Monad endpoint says: "limited to a 100 range"
            raise ChainDown(
                "https://rpc.example: eth_getLogs: eth_getLogs is limited to a 100 range"
            )
        self.log_ranges.append((start, end))
        return [log for log in self.logs if start <= int(str(log["blockNumber"]), 16) <= end]

    def rpc_eth_getTransactionReceipt(self, tx_hash: str) -> dict[str, object] | None:
        return self.receipts.get(tx_hash)

    def rpc_eth_getBlockByNumber(self, number: str, full: bool) -> dict[str, object]:
        return {"timestamp": hex(self.block_timestamp(int(number, 16))), "number": number}


def make_chain(node: FakeNode, **kw: object) -> JsonRpcChain:
    args: dict[str, object] = {
        "chain_id": 10143,
        "contract": CONTRACT,
        "account": ACCOUNT,
        "gas_margin": 1.05,
        "from_block": 69_218_030,
    }
    args.update(kw)
    return JsonRpcChain(node, **args)  # type: ignore[arg-type]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_commit_calldata_is_what_cast_produces() -> None:
    node = FakeNode()
    make_chain(node).send_commit(ROOT, 940)
    (_, params) = next(c for c in node.calls if c[0] == "eth_estimateGas")
    assert params[0]["data"] == COMMIT_CALLDATA  # type: ignore[index]
    assert params[0]["to"].lower() == CONTRACT.lower()  # type: ignore[index, union-attr]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_signed_transaction_recovers_to_the_signer_with_chain_nonce_and_tight_gas() -> None:
    node = FakeNode()
    sent = make_chain(node).send_commit(ROOT, 940)

    raw = node.raw[0]
    assert Account.recover_transaction(raw) == ACCOUNT.address
    nonce, gas_price, gas, to, value, data, v, _r, _s = rlp.decode(bytes.fromhex(raw[2:]))
    assert int.from_bytes(nonce, "big") == 7 and sent.nonce == 7
    assert int.from_bytes(gas_price, "big") == 103 * 10**9
    assert int.from_bytes(gas, "big") == int(79_455 * 1.05)  # Monad charges the limit: no slack
    assert "0x" + to.hex() == CONTRACT.lower() and int.from_bytes(value, "big") == 0
    assert "0x" + data.hex() == COMMIT_CALLDATA
    assert (int.from_bytes(v, "big") - 35) // 2 == 10143  # EIP-155: replay-protected on this chain
    assert sent.tx_hash == "0x" + "cd" * 32


@pytest.mark.trace("REQ-INFRA-007")
def test_a_commit_is_read_at_the_requested_block_tag_and_zero_means_absent() -> None:
    node = FakeNode()
    chain = make_chain(node)
    assert chain.commit_of(ROOT) is None

    node.committed[ROOT.hex()] = (940, 1_791_460_000, ACCOUNT.address)
    assert chain.commit_of(ROOT) == (940, 1_791_460_000, ACCOUNT.address)
    chain.commit_of(ROOT, finalized=True)
    tags = [p[1] for m, p in node.calls if m == "eth_call"]
    assert tags[-2:] == ["latest", "finalized"]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_commit_evidence_is_found_by_time_and_never_asks_for_more_than_a_hundred_blocks() -> (
    None
):
    """The public node answers `eth_getLogs is limited to a 100 range`. The first version asked for
    the logs from the contract's deployment block to the head -- 104,000 blocks -- and the first
    real commit could never be confirmed. The block is found from the commit's own time instead."""
    node = FakeNode()
    commit_block = FakeNode.BASE_BLOCK + 100_000
    block_time = node.block_timestamp(commit_block)
    node.committed[ROOT.hex()] = (940, block_time, ACCOUNT.address)
    node.logs = [
        {
            "transactionHash": "0x" + "12" * 32,
            "blockNumber": hex(commit_block),
            "topics": [COMMITTED_TOPIC, "0x" + ROOT.hex()],
        }
    ]

    evidence = make_chain(node).committed_event(ROOT)

    assert evidence is not None
    assert (evidence.tx_hash, evidence.block_number) == ("0x" + "12" * 32, commit_block)
    assert evidence.block_time == block_time  # the block's own timestamp, from the chain
    assert node.log_ranges, "the logs were never asked for"
    assert all(end - start + 1 <= 100 for start, end in node.log_ranges)
    # ... and never before the deployment, nor beyond the head.
    assert all(
        start >= FakeNode.BASE_BLOCK and end <= FakeNode.HEAD for start, end in node.log_ranges
    )
    # A search that bisects, not one that walks: a hundred thousand blocks in a few dozen calls.
    assert sum(1 for m, _ in node.calls if m == "eth_getBlockByNumber") < 60


@pytest.mark.trace("REQ-INFRA-007")
def test_blocks_that_share_a_second_are_all_searched() -> None:
    node = FakeNode()
    commit_block = (
        FakeNode.BASE_BLOCK + 3_001
    )  # the last block of its second: three blocks share it
    node.committed[ROOT.hex()] = (940, node.block_timestamp(commit_block), ACCOUNT.address)
    node.logs = [
        {
            "transactionHash": "0x" + "34" * 32,
            "blockNumber": hex(commit_block),
            "topics": [COMMITTED_TOPIC, "0x" + ROOT.hex()],
        }
    ]
    evidence = make_chain(node).committed_event(ROOT)
    assert evidence is not None and evidence.block_number == commit_block


@pytest.mark.trace("REQ-INFRA-007")
def test_a_root_the_chain_does_not_hold_has_no_evidence_and_costs_no_log_query() -> None:
    node = FakeNode()
    assert make_chain(node).committed_event(ROOT) is None
    assert node.log_ranges == []


@pytest.mark.trace("REQ-INFRA-007")
def test_a_receipt_is_decoded_and_a_missing_one_is_none() -> None:
    node = FakeNode()
    chain = make_chain(node)
    assert chain.receipt("0x" + "01" * 32) is None
    node.receipts["0x" + "01" * 32] = {"status": "0x1", "blockNumber": hex(70_000_000)}
    receipt = chain.receipt("0x" + "01" * 32)
    assert receipt is not None and (receipt.status, receipt.block_number) == (1, 70_000_000)
    node.receipts["0x" + "02" * 32] = {"status": "0x0", "blockNumber": hex(70_000_001)}
    failed = chain.receipt("0x" + "02" * 32)
    assert failed is not None and failed.status == 0


@pytest.mark.trace("REQ-INFRA-007")
def test_startup_refuses_a_wrong_chain_or_a_signer_that_is_not_the_owner() -> None:
    make_chain(FakeNode()).verify_ready()  # the good case does not raise

    with pytest.raises(WrongChain, match="10143.*1|1.*10143"):
        make_chain(FakeNode(chain_id=1)).verify_ready()
    with pytest.raises(NotOwner, match="owner"):
        make_chain(FakeNode(owner="0x" + "07" * 20)).verify_ready()


# ---- transport -----------------------------------------------------------------------------------


def client(handler) -> httpx.Client:  # type: ignore[no-untyped-def]
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.mark.trace("REQ-INFRA-007")
def test_the_http_transport_speaks_json_rpc() -> None:
    seen: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": "0x279f"})

    send = http_transport("https://rpc.example/v1/key", client=client(handler))
    assert send("eth_chainId", []) == "0x279f"
    assert seen[0]["method"] == "eth_chainId" and seen[0]["jsonrpc"] == "2.0"


@pytest.mark.trace("REQ-INFRA-007")
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "nonce too low"}},
        ),
        httpx.Response(500, text="upstream exploded"),
        httpx.Response(200, text="<html>not json</html>"),
    ],
    ids=["rpc error", "http 500", "not json"],
)
def test_every_way_the_node_can_fail_is_a_chain_down(response: httpx.Response) -> None:
    send = http_transport("https://rpc.example", client=client(lambda request: response))
    with pytest.raises(ChainDown):
        send("eth_chainId", [])


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unreachable_node_is_a_chain_down() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ChainDown, match="connection refused"):
        http_transport("https://rpc.example", client=client(refuse))("eth_chainId", [])


# ---- the keystore, and what must never appear ----------------------------------------------------


def write_keystore(directory: Path) -> tuple[Path, Path]:
    keystore = directory / "keystore.json"
    keystore.write_text(json.dumps(Account.encrypt(ACCOUNT.key, PASSWORD)))
    password = directory / "keystore.pass"
    password.write_text(PASSWORD + "\n")
    return keystore, password


@pytest.mark.trace("REQ-INFRA-007")
def test_a_foundry_keystore_decrypts_to_the_account_that_was_put_in(tmp_path: Path) -> None:
    keystore, password = write_keystore(tmp_path)
    assert load_signer(keystore, password).address == ACCOUNT.address


@pytest.mark.trace("REQ-INFRA-007")
def test_a_wrong_password_or_a_missing_file_fails_without_saying_either_secret(
    tmp_path: Path,
) -> None:
    keystore, _ = write_keystore(tmp_path)
    wrong = tmp_path / "wrong.pass"
    wrong.write_text("not the password\n")

    with pytest.raises(ValueError) as bad_password:
        load_signer(keystore, wrong)
    with pytest.raises(FileNotFoundError):
        load_signer(tmp_path / "absent.json", wrong)

    text = str(bad_password.value)
    assert "not the password" not in text and PASSWORD not in text
    assert ACCOUNT.key.hex() not in text


@pytest.mark.trace("REQ-INFRA-007")
def test_neither_the_key_nor_the_password_nor_a_provider_token_reaches_any_message() -> None:
    secret_url = "https://user:hunter2@rpc.example/path/TOKEN123?apikey=XYZ789"

    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot connect to {request.url}", request=request)

    chain = make_chain(FakeNode())
    chain.transport = http_transport(secret_url, client=client(refuse))  # type: ignore[attr-defined]
    with pytest.raises(ChainDown) as error:
        chain.balance_wei()

    forbidden = ["hunter2", "TOKEN123", "XYZ789", ACCOUNT.key.hex(), PASSWORD]
    for text in (str(error.value), repr(chain), repr(ACCOUNT.address)):
        assert not [bad for bad in forbidden if bad in text], text
    assert "rpc.example" in str(error.value)  # the host helps an operator and is not a secret
