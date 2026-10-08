"""The outbox: form, send, confirm, reconcile, drain (REQ-INFRA-007).

# @trace: REQ-INFRA-007

One `tick` does everything the service has to do, and **never raises on an ordinary failure**: the
notary is the one component whose job is to keep trying, and a loop that a network error can end
is not that. Each step is one of four things the chain can do to it -- be unreachable, accept a
transaction the process then loses track of, be slow to finalize, or be short of funds -- and each
has a written answer.

**Reconcile before sending.** Whatever the state of a batch, the first question is whether the
chain already has its root. A crash between sending and recording, a timeout after the node
accepted the transaction, a restart: all of them end with "found on chain", not a second send. The
contract would reject the duplicate anyway; asking first means it is never tried, and the batch is
confirmed with the evidence the chain itself holds.

**Confirmed means finalized.** A receipt, plus the root read back from the contract at the
`finalized` block tag. Visible is not enough: that is the line between "the transaction was
included" and "this will not be reorganised away".

**In order.** A batch that cannot proceed holds the ones behind it; nonces and the story the log
tells both depend on it.

**Never past a limit.** Below the balance floor or above the gas-price ceiling a batch is *held*,
with the reason recorded once. The service never tops anything up.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.batcher import NotWholeSecond, form_batch, repair_orphans
from channelflow.notary.chain import NotaryChain

SECOND_NS = 1_000_000_000


@dataclass(frozen=True)
class SubmitterConfig:
    window_ns: int
    max_batch: int
    min_balance_wei: int
    max_gas_price_wei: int
    #: How long a sent transaction may go without a receipt before it is looked at again.
    submit_timeout_ns: int


@dataclass
class TickReport:
    formed: int = 0
    sent: int = 0
    confirmed: int = 0
    held: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class OutboxSummary:
    unbatched_records: int
    unconfirmed_batches: int
    unnotarizable_records: int
    oldest_pending_age_s: float
    last_error: str


def outbox_states(catalog: Catalog) -> list[tuple[tables.Row, tables.Row]]:
    """Every batch with its state, oldest first. A batch with no event yet is `formed`."""
    states = tables.batch_states(tables.events_table(catalog))
    batches = sorted(
        tables.batches_table(catalog).read().to_pylist(),
        key=lambda r: (int(str(r["max_bar_close_time_ns"])), str(r["batch_root"])),
    )
    out: list[tuple[tables.Row, tables.Row]] = []
    for batch in batches:
        root = str(batch["batch_root"])
        state = states.get(root) or tables.event_row(
            root, "formed", at_ns=int(str(batch["formed_at_ns"]))
        )
        out.append((batch, state))
    return out


def outbox_summary(catalog: Catalog, *, now_ns: int) -> OutboxSummary:
    """What waits, how long, and the last thing that went wrong.

    The age is of the oldest unconfirmed **record**, from the moment it was registered: the wait
    an operator cares about, which keeps growing across batching, retries and holds instead of
    resetting when a batch is formed.
    """
    records = tables.records_table(catalog).read().to_pylist()
    registered = {str(r["record_id"]): int(str(r["registered_at_ns"])) for r in records}
    waiting = tables.unbatched(tables.records_table(catalog), tables.leaves_table(catalog))
    pending = [(b, s) for b, s in outbox_states(catalog) if s["event"] != "confirmed"]
    pending_roots = {str(b["batch_root"]) for b, _ in pending}

    waited = [registered[str(r["record_id"])] for r in waiting]
    waited += [
        registered[str(leaf["record_id"])]
        for leaf in tables.leaves_table(catalog).read().to_pylist()
        if str(leaf["batch_root"]) in pending_roots and str(leaf["record_id"]) in registered
    ]
    problems = [s for _, s in pending if s["event"] in ("failed", "held")]
    latest = max(problems, key=lambda s: int(str(s["event_at_ns"])), default=None)
    return OutboxSummary(
        unbatched_records=len(waiting),
        unconfirmed_batches=len(pending),
        unnotarizable_records=sum(1 for r in records if r["notarizable"] == "no"),
        oldest_pending_age_s=(now_ns - min(waited)) / SECOND_NS if waited else 0.0,
        last_error=str(latest["detail"]) if latest is not None else "",
    )


class Submitter:
    def __init__(
        self,
        *,
        catalog: Catalog,
        chain: NotaryChain,
        config: SubmitterConfig,
        now_ns: Callable[[], int],
    ) -> None:
        self.catalog = catalog
        self.chain = chain
        self.config = config
        self.now_ns = now_ns

    # ---- one pass over everything --------------------------------------------------------------

    def tick(self) -> TickReport:
        report = TickReport()
        try:
            repair_orphans(self.catalog, now_ns=self.now_ns(), window_ns=self.config.window_ns)
            while form_batch(
                self.catalog,
                now_ns=self.now_ns(),
                window_ns=self.config.window_ns,
                max_batch=self.config.max_batch,
            ):
                report.formed += 1
        except NotWholeSecond as error:
            report.errors.append(f"cannot form a batch: {error}")
        except Exception as error:  # noqa: BLE001 -- the loop must survive its own bugs
            report.errors.append(f"batching failed: {type(error).__name__}: {error}")

        try:
            pending = [(b, s) for b, s in outbox_states(self.catalog) if s["event"] != "confirmed"]
        except Exception as error:  # noqa: BLE001
            report.errors.append(f"could not read the outbox: {type(error).__name__}: {error}")
            return report
        for batch, state in pending:
            if not self._advance(batch, state, report):
                break  # in order: whatever is behind this waits
        return report

    # ---- one batch ------------------------------------------------------------------------------

    def _advance(self, batch: tables.Row, state: tables.Row, report: TickReport) -> bool:
        root_hex = str(batch["batch_root"])
        root = bytes.fromhex(root_hex)
        attempt = int(str(state["attempt"]))
        try:
            return self._advance_unguarded(batch, state, root, root_hex, attempt, report)
        except Exception as error:  # noqa: BLE001 -- one batch's trouble is not the loop's
            detail = f"{type(error).__name__}: {error}"
            report.errors.append(f"{root_hex[:12]}: {detail}")
            report.failed += 1
            self._event(root_hex, "failed", attempt=attempt, detail=detail)
            return False

    def _advance_unguarded(
        self,
        batch: tables.Row,
        state: tables.Row,
        root: bytes,
        root_hex: str,
        attempt: int,
        report: TickReport,
    ) -> bool:
        event = str(state["event"])
        sent_before = event == "submitted" and bool(state["tx_hash"])

        # 1. Reconcile: does the chain already have this root?
        if self.chain.commit_of(root) is not None:
            return self._confirm_if_final(root, root_hex, state, attempt, sent_before, report)

        # 2. A transaction we sent and have not seen the end of.
        if sent_before:
            receipt = self.chain.receipt(str(state["tx_hash"]))
            if receipt is not None and receipt.status != 1:
                report.failed += 1
                self._event(root_hex, "failed", attempt=attempt, detail="transaction reverted")
                return False
            waited = self.now_ns() - int(str(state["event_at_ns"]))
            if receipt is None and waited < self.config.submit_timeout_ns:
                return False  # still in flight; asking again is free, sending again is not

        # 3. Limits: nothing is sent past them.
        reason = self._limit_reached()
        if reason is not None:
            if not (event == "held" and state["detail"] == reason):
                self._event(root_hex, "held", attempt=attempt, detail=reason)
            report.held += 1
            return False

        # 4. Send.
        bar_ts = int(str(batch["max_bar_close_time_ns"])) // SECOND_NS
        try:
            sent = self.chain.send_commit(root, bar_ts)
        except Exception as error:  # noqa: BLE001 -- unknown outcome: the next tick asks the chain
            detail = str(error) or type(error).__name__
            report.failed += 1
            report.errors.append(f"{root_hex[:12]}: {detail}")
            self._event(root_hex, "failed", attempt=attempt + 1, detail=detail)
            return False
        report.sent += 1
        self._event(
            root_hex,
            "submitted",
            attempt=attempt + 1,
            tx_hash=sent.tx_hash,
            nonce=sent.nonce,
        )

        receipt = self.chain.receipt(sent.tx_hash)
        if receipt is not None and receipt.status != 1:
            report.failed += 1
            self._event(root_hex, "failed", attempt=attempt + 1, detail="transaction reverted")
            return False
        if receipt is not None and self.chain.commit_of(root, finalized=True) is not None:
            submitted = tables.event_row(
                root_hex,
                "submitted",
                at_ns=self.now_ns(),
                attempt=attempt + 1,
                tx_hash=sent.tx_hash,
            )
            return self._confirm_if_final(root, root_hex, submitted, attempt + 1, True, report)
        return False

    def _confirm_if_final(
        self,
        root: bytes,
        root_hex: str,
        state: tables.Row,
        attempt: int,
        sent_before: bool,
        report: TickReport,
    ) -> bool:
        final = self.chain.commit_of(root, finalized=True)
        if final is None:
            return False  # visible, not yet final
        _bar_ts, block_time, _committer = final
        if sent_before:
            # Our own transaction: its block is in its receipt. No log search -- that is for a
            # commit found on the chain that this process never recorded, and the public node
            # limits it.
            receipt = self.chain.receipt(str(state["tx_hash"]))
            tx_hash = str(state["tx_hash"])
            block_number = receipt.block_number if receipt is not None else -1
        else:
            evidence = self.chain.committed_event(root)
            tx_hash = evidence.tx_hash if evidence else ""
            block_number = evidence.block_number if evidence is not None else -1
        self._event(
            root_hex,
            "confirmed",
            attempt=attempt,
            tx_hash=tx_hash,
            block_number=block_number,
            block_time_s=block_time,
            detail="" if sent_before else "found on chain",
        )
        report.confirmed += 1
        return True

    def _limit_reached(self) -> str | None:
        balance = self.chain.balance_wei()
        if balance < self.config.min_balance_wei:
            return (
                f"balance {balance} wei is below the floor {self.config.min_balance_wei} wei; "
                "nothing is sent until it is topped up"
            )
        price = self.chain.gas_price_wei()
        if price > self.config.max_gas_price_wei:
            return f"gas price {price} wei is above the ceiling {self.config.max_gas_price_wei} wei"
        return None

    def _event(self, root_hex: str, event: str, **fields: object) -> None:
        tables.append_rows(
            tables.events_table(self.catalog),
            [tables.event_row(root_hex, event, at_ns=self.now_ns(), **fields)],  # type: ignore[arg-type]
        )
