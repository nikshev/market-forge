# @trace: REQ-INFRA-007
"""Registration: what a pass registers, once, without changing what it writes (FR-004…FR-010)."""

from __future__ import annotations

from pathlib import Path

import pytest

from channelflow.backtest import BacktestRunner
from channelflow.bus import EventBus
from channelflow.events import CandidateUpdated, ChannelFitted
from channelflow.lakehouse import Catalog
from channelflow.notary import tables as notary_tables
from channelflow.notary.context import NotaryContext, build_context
from channelflow.notary.registrar import Registrar
from channelflow.notary.scheme import Context, record_hash_hex
from channelflow.pipeline import record_replay
from channelflow.signals import Candidate
from channelflow.tables import channels as channels_table
from channelflow.tables import signals as signals_table
from tests.unit.pipeline.test_replay import MINUTE_NS, rising_with_rejections

COMMIT = "0123456789abcdef0123456789abcdef01234567"
DATASET = (14_020, "96f5ba7db274aa80" * 4)
VENUE, SYMBOL = "binance", "BTCUSDT"


def good_context(**overrides: object) -> NotaryContext:
    args: dict[str, object] = {
        "gap_threshold": 1,
        "dataset": DATASET,
        "code_commit": COMMIT,
        "code_dirty": "false",
    }
    args.update(overrides)
    return build_context(BacktestRunner(), **args)  # type: ignore[arg-type]


def make_registrar(catalog: Catalog, *, from_ns: int = 0, context: NotaryContext | None = None):  # type: ignore[no-untyped-def]
    table = notary_tables.records_table(catalog)
    return Registrar(
        records_table=table,
        context=context or good_context(),
        from_ns=from_ns,
        registered=notary_tables.registered_ids(table),
    )


def replay(catalog: Catalog, registrar: Registrar, bars: list, seen: list[Candidate] | None = None):  # type: ignore[no-untyped-def]
    bus = EventBus()
    bus.subscribe(ChannelFitted, registrar.snapshot_handler(VENUE, SYMBOL, MINUTE_NS))
    bus.subscribe(CandidateUpdated, registrar.decision_handler())
    if seen is not None:
        bus.subscribe(CandidateUpdated, lambda event: seen.append(event.candidate))
    return record_replay(
        bars, catalog=catalog, venue=VENUE, symbol=SYMBOL, timeframe_ns=MINUTE_NS, bus=bus
    )


def _fresh_catalog(home):  # type: ignore[no-untyped-def]
    from channelflow.lakehouse import catalog as open_catalog

    home.mkdir(parents=True, exist_ok=True)
    return open_catalog(uri=f"sqlite:///{home}/catalog.db", warehouse=str(home))


def registered_rows(catalog: Catalog) -> list[dict[str, object]]:
    return notary_tables.records_table(catalog).read().to_pylist()


@pytest.mark.trace("REQ-INFRA-007")
def test_a_pass_registers_each_snapshot_once_and_the_hash_can_be_recomputed(
    catalog: Catalog,
) -> None:
    registrar = make_registrar(catalog)
    recording, _ = replay(catalog, registrar, rising_with_rejections())
    assert registrar.flush() > 0

    snapshots = [r for r in registered_rows(catalog) if r["kind"] == "snapshot"]
    stored = channels_table.table_for(catalog).read().to_pylist()
    assert len(snapshots) == len(stored) == recording.channel_snapshots
    assert len({r["record_id"] for r in snapshots}) == len(snapshots)

    # Recompute from the stored row plus the three context values: the committed value.
    ctx = good_context()
    by_as_of = {row["as_of_ns"]: row for row in stored}
    for registered in snapshots:
        as_of = int(str(registered["record_id"]).rsplit("|", 1)[1])
        # The stored row, read back and re-encoded, is the registered record: what the lakehouse
        # holds and what the notary hashed are the same bytes (no second definition of a snapshot).
        stored_snapshot = channels_table.from_row(by_as_of[as_of])
        stored_row = channels_table.to_row(
            stored_snapshot, venue=VENUE, symbol=SYMBOL, timeframe_ns=MINUTE_NS
        )
        assert registered["record_bytes"] == channels_table.SCHEMA.encode_row(stored_row).hex()
        assert registered["record_hash"] == record_hash_hex(
            "snapshot",
            bytes.fromhex(str(registered["record_bytes"])),
            Context(ctx.config_hash, ctx.dataset_ref, ctx.code_commit),
        )
        assert registered["notarizable"] == "yes" and registered["reason"] == ""
        assert registered["dataset_snapshot_id"] == DATASET[0]


@pytest.mark.trace("REQ-INFRA-007")
def test_a_second_pass_over_the_same_data_registers_nothing(catalog: Catalog) -> None:
    bars = rising_with_rejections()
    first = make_registrar(catalog)
    replay(catalog, first, bars)
    first.flush()
    before = registered_rows(catalog)

    second = make_registrar(catalog, context=good_context(dataset=(14_999, "ff" * 32)))
    replay(catalog, second, bars)

    assert second.flush() == 0
    assert registered_rows(catalog) == before  # not one row, and not one with the newer dataset


@pytest.mark.trace("REQ-INFRA-007")
def test_a_crash_between_the_lakehouse_write_and_the_registration_loses_nothing(
    catalog: Catalog,
) -> None:
    bars = rising_with_rejections()
    lost = make_registrar(catalog)
    replay(
        catalog, lost, bars
    )  # the snapshots reach the lakehouse; the process dies before flush()
    assert registered_rows(catalog) == []
    assert channels_table.table_for(catalog).read().num_rows > 0

    after_restart = make_registrar(catalog)
    replay(catalog, after_restart, bars)  # the recorder skips what it wrote; the bus still fires

    assert after_restart.flush() > 0
    snapshots = [r for r in registered_rows(catalog) if r["kind"] == "snapshot"]
    assert len(snapshots) == channels_table.table_for(catalog).read().num_rows


@pytest.mark.trace("REQ-INFRA-007")
def test_records_before_the_epoch_are_not_registered(catalog: Catalog) -> None:
    bars = rising_with_rejections()
    everything = make_registrar(catalog)
    replay(catalog, everything, bars)
    all_times = sorted(
        int(str(r.record_id).split("|")[-1])
        for r in everything._pending  # noqa: SLF001 -- the buffer is what is under test
        if r.kind == "snapshot"
    )
    epoch = all_times[len(all_times) // 2]

    late = make_registrar(catalog, from_ns=epoch)
    replay(catalog, late, bars)
    registered = [r for r in late._pending if r.kind == "snapshot"]  # noqa: SLF001

    assert 0 < len(registered) < len(all_times)
    assert all(r.bar_close_time_ns >= epoch for r in registered)


@pytest.mark.trace("REQ-INFRA-007")
def test_every_transition_of_every_candidate_is_registered_once(catalog: Catalog) -> None:
    seen: list[Candidate] = []
    registrar = make_registrar(catalog)
    replay(catalog, registrar, rising_with_rejections(), seen)
    registrar.flush()

    latest: dict[int, Candidate] = {}
    for candidate in seen:
        latest[candidate.opened_at_ns] = candidate
    expected = sum(len(c.history) for c in latest.values())
    decisions = [r for r in registered_rows(catalog) if r["kind"] == "decision"]

    assert expected > 0
    assert len(decisions) == expected
    assert len({r["record_id"] for r in decisions}) == expected


@pytest.mark.trace("REQ-INFRA-007")
def test_a_terminal_outcome_the_signals_table_never_received_is_still_registered(
    catalog: Catalog, tmp_path: Path
) -> None:
    """The defect found while planning: `SignalRecorder` writes a candidate once, at first sight,
    and never appends its later transitions. The notary takes decisions from the bus instead."""
    bars = rising_with_rejections()
    survey: list[Candidate] = []
    replay(catalog, make_registrar(catalog), bars, survey)
    # Cut the series just after some candidate opened that went on to a longer history.
    longest = max({c.opened_at_ns: c for c in survey}.values(), key=lambda c: len(c.history))
    assert len(longest.history) > 1, "the fixture needs a candidate with a history"
    cut = next(
        i for i, b in enumerate(bars) if b.close_time_ns == longest.history[0].bar_close_time_ns
    )
    # A fresh plane, so the survey above did not already write the signals table.
    fresh = _fresh_catalog(tmp_path / "second")
    early = make_registrar(fresh)
    replay(fresh, early, bars[: cut + 1])  # the candidate is live at the cut
    early.flush()
    full = make_registrar(fresh)
    replay(fresh, full, bars)
    full.flush()

    signal_id = next(
        str(r["signal_id"])
        for r in signals_table.table_for(fresh).read().to_pylist()
        if r["opened_at_ns"] == longest.opened_at_ns
    )
    in_table = [
        r
        for r in signals_table.transitions_table_for(fresh).read().to_pylist()
        if r["signal_id"] == signal_id
    ]
    registered = [
        r
        for r in registered_rows(fresh)
        if r["kind"] == "decision" and str(r["record_id"]).startswith(f"decision|{signal_id}|")
    ]

    assert len(in_table) == 1  # the table froze the candidate at first sight
    assert len(registered) == len(longest.history) > len(in_table)  # the notary did not


@pytest.mark.trace("REQ-INFRA-007")
def test_a_bar_that_is_not_final_is_refused_and_counted_never_registered(catalog: Catalog) -> None:
    registrar = make_registrar(catalog)
    bars = rising_with_rejections()
    bus = EventBus()
    handler = registrar.snapshot_handler(VENUE, SYMBOL, MINUTE_NS)
    bus.subscribe(
        ChannelFitted,
        lambda event: handler(
            ChannelFitted(
                bar=event.bar.model_copy(update={"is_final": False}), snapshot=event.snapshot
            )
        ),
    )
    record_replay(
        bars, catalog=catalog, venue=VENUE, symbol=SYMBOL, timeframe_ns=MINUTE_NS, bus=bus
    )

    assert registrar.refused > 0
    assert registrar.flush() == 0
    assert registered_rows(catalog) == []


@pytest.mark.trace("REQ-INFRA-007")
def test_an_unnotarizable_context_stores_the_record_with_the_reason_and_no_hash(
    catalog: Catalog,
) -> None:
    registrar = make_registrar(catalog, context=good_context(code_commit=None))
    replay(catalog, registrar, rising_with_rejections())
    registrar.flush()

    rows = registered_rows(catalog)
    assert rows and all(r["notarizable"] == "no" for r in rows)
    assert all(r["record_hash"] == "" and "commit" in str(r["reason"]) for r in rows)
    assert all(r["record_bytes"] for r in rows)  # the record is kept; only the claim is withheld
