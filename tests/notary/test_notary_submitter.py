# @trace: REQ-INFRA-007
"""The outbox: send, confirm, reconcile, drain -- and survive (FR-006…FR-009, FR-016)."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.batcher import Batch, Leaf, write_batch
from channelflow.notary.chain import ChainDown
from channelflow.notary.scheme import merkle_root
from channelflow.notary.submitter import Submitter, SubmitterConfig, outbox_summary
from tests.notary.conftest import SECOND, FakeNotaryChain, record_row, register

WINDOW = 30 * 60 * SECOND
T = 1_791_450_000
NOW = T * SECOND + WINDOW + 60 * SECOND


def config(**changes: object) -> SubmitterConfig:
    base: dict[str, object] = {
        "window_ns": WINDOW,
        "max_batch": 100,
        "min_balance_wei": 10**17,
        "max_gas_price_wei": 500 * 10**9,
        "submit_timeout_ns": 120 * SECOND,
    }
    base.update(changes)
    return SubmitterConfig(**base)  # type: ignore[arg-type]


def submitter(
    catalog: Catalog, chain: FakeNotaryChain, *, clock: list[int] | None = None, **kw: object
):  # type: ignore[no-untyped-def]
    now = clock if clock is not None else [NOW]
    return Submitter(catalog=catalog, chain=chain, config=config(**kw), now_ns=lambda: now[0])


def events(catalog: Catalog) -> list[tuple[str, str]]:
    return [
        (str(r["event"]), str(r["detail"]))
        for r in sorted(
            tables.events_table(catalog).read().to_pylist(), key=lambda r: r["event_at_ns"]
        )
    ]


def one_record(catalog: Catalog, name: str = "a", at: int = T) -> None:
    register(catalog, record_row(name, at, registered_at_ns=T * SECOND))


@pytest.mark.trace("REQ-INFRA-007")
def test_a_formed_batch_is_sent_once_and_confirmed_from_the_chain(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    submitter(catalog, chain).tick()

    assert len(chain.sent) == 1
    root, bar_ts = chain.sent[0]
    assert bar_ts == T
    state = tables.batch_states(tables.events_table(catalog))[root.hex()]
    assert state["event"] == "confirmed"
    assert state["block_time_s"] == chain.block_ts  # the chain's time, not ours
    assert state["block_number"] == chain.block_number and str(state["tx_hash"]).startswith("0x")
    assert [e for e, _ in events(catalog)] == ["formed", "submitted", "confirmed"]


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unreachable_chain_loses_nothing_and_the_same_root_is_retried(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.down = True
    sub = submitter(catalog, chain)
    sub.tick()
    sub.tick()
    root = tables.batches_table(catalog).read().to_pylist()[0]["batch_root"]

    assert chain.sent == [] and tables.batches_table(catalog).read().num_rows == 1
    assert [e for e, _ in events(catalog)] == ["formed", "failed", "failed"]
    assert "connection refused" in events(catalog)[-1][1]

    chain.down = False
    sub.tick()
    assert [r.hex() for r, _ in chain.sent] == [root]  # sent exactly once, the same root
    assert events(catalog)[-1][0] == "confirmed"


@pytest.mark.trace("REQ-INFRA-007")
def test_a_failure_after_the_chain_accepted_the_transaction_is_reconciled_not_resent(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    """The process records nothing it did not see: a timeout after the node accepted the transaction
    looks like a failure. The next tick asks the chain first and finds the root there."""
    one_record(catalog)
    chain.crash_after_send = True
    sub = submitter(catalog, chain)
    sub.tick()
    assert events(catalog)[-1][0] == "failed" and len(chain.sent) == 1

    sub.tick()

    assert len(chain.sent) == 1  # no second send, which the contract would have reverted anyway
    last = tables.batch_states(tables.events_table(catalog))[chain.sent[0][0].hex()]
    assert last["event"] == "confirmed" and last["detail"] == "found on chain"
    assert last["block_number"] == chain.block_number


@pytest.mark.trace("REQ-INFRA-007")
def test_a_process_that_died_before_recording_anything_finds_its_root_on_chain(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    sub = submitter(catalog, chain)
    # The batch is formed and recorded; the transaction was accepted; the process died before it
    # could write `submitted`. On restart there is only `formed`.
    from channelflow.notary.batcher import form_batch

    batch = form_batch(catalog, now_ns=NOW, window_ns=WINDOW, max_batch=100)
    assert batch is not None
    chain.send_commit(batch.root, batch.bar_ts_s)

    sub.tick()

    assert len(chain.sent) == 1
    assert events(catalog)[-1] == ("confirmed", "found on chain")


@pytest.mark.trace("REQ-INFRA-007")
def test_confirmed_means_finalized_not_merely_visible(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.finalize_after_reads = 2
    sub = submitter(catalog, chain)

    sub.tick()
    assert events(catalog)[-1][0] == "submitted"
    sub.tick()
    assert events(catalog)[-1][0] == "submitted"
    sub.tick()
    assert events(catalog)[-1][0] == "confirmed"
    assert len(chain.sent) == 1


@pytest.mark.trace("REQ-INFRA-007")
def test_a_reverted_transaction_is_a_failure_and_is_retried(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.receipt_status = 0
    sub = submitter(catalog, chain)
    sub.tick()
    assert events(catalog)[-1][0] == "failed" and "reverted" in events(catalog)[-1][1]

    chain.receipt_status = 1
    sub.tick()
    assert events(catalog)[-1][0] == "confirmed" and len(chain.sent) == 2


@pytest.mark.trace("REQ-INFRA-007")
def test_a_balance_under_the_floor_holds_the_batch_once_and_sends_nothing(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.balance = 10**15
    sub = submitter(catalog, chain)
    sub.tick()
    sub.tick()
    sub.tick()

    assert chain.sent == []
    held = [e for e in events(catalog) if e[0] == "held"]
    assert len(held) == 1 and "balance" in held[0][1]  # the reason is recorded once, not per tick

    chain.balance = 5 * 10**18  # a human topped it up
    sub.tick()
    assert events(catalog)[-1][0] == "confirmed"


@pytest.mark.trace("REQ-INFRA-007")
def test_a_gas_price_over_the_ceiling_holds_the_batch(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.gas_price = 900 * 10**9
    submitter(catalog, chain).tick()

    assert chain.sent == []
    assert events(catalog)[-1][0] == "held" and "gas price" in events(catalog)[-1][1]


@pytest.mark.trace("REQ-INFRA-007")
def test_batches_are_sent_in_order_and_a_held_one_holds_those_behind_it(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog, "a", T)
    clock = [NOW]
    sub = submitter(catalog, chain, clock=clock)
    chain.gas_price = 900 * 10**9
    sub.tick()  # batch 1 formed and held
    register(catalog, record_row("b", T + 3600, registered_at_ns=(T + 3600) * SECOND))
    clock[0] = (T + 3600) * SECOND + WINDOW
    sub.tick()  # batch 2 formed; batch 1 still held, so batch 2 must not jump the queue
    assert chain.sent == []

    chain.gas_price = 100 * 10**9
    sub.tick()

    roots = [r.hex() for r, _ in chain.sent]
    stored = sorted(
        tables.batches_table(catalog).read().to_pylist(), key=lambda r: r["max_bar_close_time_ns"]
    )
    assert roots == [r["batch_root"] for r in stored]


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unexpected_error_in_one_tick_does_not_end_the_loop(
    catalog: Catalog, chain: FakeNotaryChain, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_record(catalog)

    def broken(*args: object, **kwargs: object) -> None:
        raise ValueError("a bug, not a network error")

    monkeypatch.setattr(chain, "send_commit", broken)
    sub = submitter(catalog, chain)
    report = sub.tick()  # must not raise

    assert report.errors and "a bug" in report.errors[0]
    assert events(catalog)[-1][0] == "failed"
    monkeypatch.undo()
    sub.tick()
    assert events(catalog)[-1][0] == "confirmed"


@pytest.mark.trace("REQ-INFRA-007")
def test_leaves_written_before_a_crash_are_completed_into_a_batch_and_sent(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    """A crash after the leaves and before the batch row leaves records 'batched' into nothing."""
    rows = [record_row(n, T + i * 10, registered_at_ns=T * SECOND) for i, n in enumerate("xyz")]
    register(catalog, *rows)
    hashes = [bytes.fromhex(str(r["record_hash"])) for r in rows]
    root = merkle_root(hashes)
    leaves = tuple(
        Leaf(str(r["record_id"]), h, int(str(r["bar_close_time_ns"])), i)
        for i, (r, h) in enumerate(zip(rows, hashes, strict=True))
    )
    batch = Batch(
        root, leaves, leaves[0].bar_close_time_ns, leaves[-1].bar_close_time_ns, NOW, WINDOW
    )
    # Only the first of the three appends happened.
    from channelflow.notary.batcher import write_leaves

    write_leaves(catalog, batch)
    assert tables.batches_table(catalog).read().num_rows == 0

    submitter(catalog, chain).tick()

    assert tables.batches_table(catalog).read().num_rows == 1
    assert [r.hex() for r, _ in chain.sent] == [root.hex()]
    assert write_batch  # the public writer exists for the batcher's own use


@pytest.mark.trace("REQ-INFRA-007")
def test_the_outbox_is_visible_while_the_chain_is_down_and_drains_when_it_returns(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    chain.down = True
    clock = [T * SECOND + WINDOW]
    sub = submitter(catalog, chain, clock=clock)
    for i in range(3):  # three windows, each with a record, while the chain is unreachable
        at = T + i * 3600
        register(catalog, record_row(f"r{i}", at, registered_at_ns=at * SECOND))
        register(catalog, record_row(f"bad{i}", at, notarizable="no"))
        clock[0] = at * SECOND + WINDOW
        sub.tick()

    summary = outbox_summary(catalog, now_ns=clock[0])
    assert summary.unconfirmed_batches == 3 and summary.unbatched_records == 0
    assert summary.unnotarizable_records == 3
    assert summary.oldest_pending_age_s > 0 and "connection refused" in summary.last_error

    chain.down = False
    sub.tick()
    sub.tick()
    sub.tick()
    after = outbox_summary(catalog, now_ns=clock[0])
    assert after.unconfirmed_batches == 0 and len(chain.sent) == 3  # each once
    assert after.last_error == ""


@pytest.mark.trace("REQ-INFRA-007")
def test_a_transaction_still_in_flight_is_not_sent_again_before_its_timeout(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.unmined = True
    clock = [NOW]
    sub = submitter(catalog, chain, clock=clock)
    sub.tick()
    clock[0] += 60 * SECOND  # inside the 120 s timeout
    sub.tick()
    sub.tick()

    assert len(chain.sent) == 1  # asking again is free, sending again is not
    assert events(catalog)[-1][0] == "submitted"

    chain.mine()
    sub.tick()
    assert events(catalog)[-1][0] == "confirmed" and len(chain.sent) == 1


@pytest.mark.trace("REQ-INFRA-007")
def test_a_transaction_that_was_mined_as_a_revert_after_we_stopped_looking_is_noticed(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    one_record(catalog)
    chain.unmined = True
    sub = submitter(catalog, chain)
    sub.tick()
    chain.mine(status=0)  # included, and it reverted

    sub.tick()

    assert ("failed", "transaction reverted") in events(catalog)


@pytest.mark.trace("REQ-INFRA-007")
def test_one_batch_that_cannot_be_sent_holds_every_batch_behind_it(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    """The ordering is a promise about the log, not a politeness: B must not overtake a stuck A."""
    one_record(catalog, "a", T)
    clock = [NOW]
    sub = submitter(catalog, chain, clock=clock)
    chain.down = True
    sub.tick()  # A is formed; the chain is away
    a_root = bytes.fromhex(tables.batches_table(catalog).read().to_pylist()[0]["batch_root"])

    chain.down = False
    chain.fail_roots.add(a_root)  # now only A is refused
    register(catalog, record_row("b", T + 3600, registered_at_ns=(T + 3600) * SECOND))
    clock[0] = (T + 3600) * SECOND + WINDOW
    sub.tick()  # B is formed; A fails; B must wait behind it
    assert chain.sent == []
    assert tables.batches_table(catalog).read().num_rows == 2

    chain.fail_roots.clear()
    sub.tick()
    stored = sorted(
        tables.batches_table(catalog).read().to_pylist(), key=lambda r: r["max_bar_close_time_ns"]
    )
    assert [r.hex() for r, _ in chain.sent] == [r["batch_root"] for r in stored]


@pytest.mark.trace("REQ-INFRA-007")
def test_orphaned_leaves_that_do_not_hash_to_their_root_are_not_turned_into_a_batch(
    catalog: Catalog, chain: FakeNotaryChain
) -> None:
    """Guessing a batch from leaves that disagree with their own root is worse than waiting."""
    rows = [record_row(n, T + i * 10, registered_at_ns=T * SECOND) for i, n in enumerate("pq")]
    register(catalog, *rows)
    tables.append_rows(
        tables.leaves_table(catalog),
        [
            {
                "bar_close_time_ns": int(str(r["bar_close_time_ns"])),
                "batch_root": "ee" * 32,  # not the root of these leaves
                "ordinal": i,
                "record_id": r["record_id"],
                "record_hash": r["record_hash"],
            }
            for i, r in enumerate(rows)
        ],
    )

    submitter(catalog, chain).tick()

    assert tables.batches_table(catalog).read().num_rows == 0
    assert chain.sent == []


@pytest.mark.trace("REQ-INFRA-007")
def test_a_commit_we_sent_is_confirmed_from_its_receipt_without_searching_logs(
    catalog: Catalog, chain: FakeNotaryChain, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The log search is for a commit found on the chain that we never recorded; our own
    transaction's block is in its receipt, and the public node limits log queries to a hundred
    blocks."""
    one_record(catalog)

    def forbidden(root: bytes) -> object:
        raise AssertionError("a log search for a transaction whose receipt we hold")

    monkeypatch.setattr(chain, "committed_event", forbidden)
    submitter(catalog, chain).tick()

    state = tables.batch_states(tables.events_table(catalog))[chain.sent[0][0].hex()]
    assert state["event"] == "confirmed" and state["block_number"] == chain.block_number
    assert str(state["tx_hash"]).startswith("0x") and state["detail"] == ""


@pytest.mark.trace("REQ-INFRA-007")
def test_a_log_search_that_the_node_refuses_leaves_the_batch_pending_not_lost(
    catalog: Catalog, chain: FakeNotaryChain, monkeypatch: pytest.MonkeyPatch
) -> None:
    one_record(catalog)
    chain.crash_after_send = True
    sub = submitter(catalog, chain)
    sub.tick()  # sent, then the process "died": only `failed` is recorded
    monkeypatch.setattr(
        chain, "committed_event", lambda root: (_ for _ in ()).throw(ChainDown("413"))
    )

    sub.tick()  # found on the chain; the evidence lookup is refused
    assert events(catalog)[-1][0] == "failed" and len(chain.sent) == 1

    monkeypatch.undo()
    sub.tick()  # the node answers again: confirmed, and still not sent twice
    assert events(catalog)[-1] == ("confirmed", "found on chain") and len(chain.sent) == 1
