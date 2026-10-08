# @trace: REQ-INFRA-007
"""An in-memory chain for the notary, and rows to feed the batcher.

`FakeNotaryChain` implements the same port as `channelflow.notary.chain.JsonRpcChain` and can be
made to fail in exactly the ways the submitter has to survive: unreachable, dying between sending
and recording, slow to finalize, short of funds. It also enforces what the real contract enforces --
a root is committed once -- so a test cannot pass by sending the same batch twice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.chain import ChainDown, CommitEvidence, Receipt, SentTx

SIGNER = "0x2A3b97f9e0454Ed44d016FE92ccBCEcF8Cf02131"
ZERO = "0x" + "00" * 20


@dataclass
class FakeNotaryChain:
    balance: int = 5 * 10**18
    gas_price: int = 103 * 10**9
    block_ts: int = 1_791_460_000
    # behaviour knobs
    down: bool = False
    #: Raise `Crash` right after the transaction is accepted -- before the caller can record it.
    crash_after_send: bool = False
    #: A root is visible at `latest` at once but at `finalized` only after this many reads.
    finalize_after_reads: int = 0
    receipt_status: int = 1
    #: Transactions are accepted but not mined: no receipt and no commit until `mine()`.
    unmined: bool = False
    #: Roots whose send fails (a per-batch fault, as opposed to a node that is down).
    fail_roots: set[bytes] = field(default_factory=set)
    # state
    commits: dict[bytes, tuple[int, int, str, str, int]] = field(default_factory=dict)
    sent: list[tuple[bytes, int]] = field(default_factory=list)
    _finalized_reads: dict[bytes, int] = field(default_factory=dict)
    _receipts: dict[str, Receipt] = field(default_factory=dict)
    _pending: dict[str, tuple[bytes, int, int]] = field(default_factory=dict)
    block_number: int = 69_300_000
    nonce: int = 0

    class Crash(RuntimeError):
        """The process died after the chain accepted the transaction."""

    def _check(self) -> None:
        if self.down:
            raise ChainDown("connection refused")

    # ---- the port ---------------------------------------------------------------------------
    def chain_id(self) -> int:
        self._check()
        return 10143

    def signer_address(self) -> str:
        return SIGNER

    def balance_wei(self) -> int:
        self._check()
        return self.balance

    def gas_price_wei(self) -> int:
        self._check()
        return self.gas_price

    def commit_of(self, root: bytes, *, finalized: bool = False) -> tuple[int, int, str] | None:
        self._check()
        entry = self.commits.get(root)
        if entry is None:
            return None
        if finalized:
            reads = self._finalized_reads.get(root, 0) + 1
            self._finalized_reads[root] = reads
            if reads <= self.finalize_after_reads:
                return None
        bar_ts, block_time, committer, _tx, _block = entry
        return bar_ts, block_time, committer

    def committed_event(self, root: bytes) -> CommitEvidence | None:
        self._check()
        entry = self.commits.get(root)
        if entry is None:
            return None
        _bar, block_time, _committer, tx, block = entry
        return CommitEvidence(tx_hash=tx, block_number=block, block_time=block_time)

    def send_commit(self, root: bytes, bar_ts: int) -> SentTx:
        self._check()
        if root in self.fail_roots:
            raise ChainDown("execution reverted: this batch cannot be sent")
        if root in self.commits:  # what the contract does
            raise ChainDown("execution reverted: AlreadyCommitted")
        self.nonce += 1
        self.block_number += 1
        tx = "0x" + format(0x5000 + self.nonce, "064x")
        self.sent.append((root, bar_ts))
        if self.unmined:
            self._pending[tx] = (root, bar_ts, self.block_number)
        else:
            self._land(tx, root, bar_ts, self.block_number, self.receipt_status)
        if self.crash_after_send:
            self.crash_after_send = False
            raise self.Crash("process died")
        return SentTx(tx_hash=tx, nonce=self.nonce)

    def _land(self, tx: str, root: bytes, bar_ts: int, block: int, status: int) -> None:
        if status == 1:  # a reverted transaction commits nothing
            self.commits[root] = (bar_ts, self.block_ts, SIGNER, tx, block)
        self._receipts[tx] = Receipt(status=status, block_number=block)

    def mine(self, status: int = 1) -> None:
        """Include every accepted-but-unmined transaction, with this receipt status."""
        for tx, (root, bar_ts, block) in list(self._pending.items()):
            self._land(tx, root, bar_ts, block, status)
        self._pending.clear()

    def receipt(self, tx_hash: str) -> Receipt | None:
        self._check()
        return self._receipts.get(tx_hash)

    def block_time(self, number: int) -> int:
        self._check()
        return self.block_ts


@pytest.fixture
def chain() -> FakeNotaryChain:
    return FakeNotaryChain()


SECOND = 1_000_000_000


def record_row(
    record_id: str,
    bar_close_s: int,
    *,
    registered_at_ns: int | None = None,
    kind: str = "snapshot",
    notarizable: str = "yes",
) -> tables.Row:
    """A registered record whose bar closed at `bar_close_s` (whole seconds, as bars do)."""
    bar_close_ns = bar_close_s * SECOND
    return {
        "bar_close_time_ns": bar_close_ns,
        "record_id": record_id,
        "kind": kind,
        "venue": "binance",
        "symbol": "BTCUSDT",
        "timeframe_ns": 300 * SECOND,
        "record_hash": (record_id.encode().hex() * 32)[:64] if notarizable == "yes" else "",
        "record_bytes": "00",
        "scheme_version": 1,
        "config_hash": "c" * 64,
        "dataset_ref": "d" * 64,
        "dataset_snapshot_id": 7,
        "code_commit": "a" * 40 if notarizable == "yes" else "",
        "notarizable": notarizable,
        "reason": "" if notarizable == "yes" else "commit absent",
        "registered_at_ns": registered_at_ns
        if registered_at_ns is not None
        else bar_close_ns + 60 * SECOND,
    }


def register(catalog: Catalog, *rows: tables.Row) -> None:
    tables.append_rows(tables.records_table(catalog), rows)
