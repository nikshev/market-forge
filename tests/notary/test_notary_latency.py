# @trace: REQ-INFRA-007
"""The figure the product may quote: per record, from the chain's time, honestly labelled."""

from __future__ import annotations

import pytest

from channelflow.lakehouse import Catalog
from channelflow.notary import tables
from channelflow.notary.latency import latency_report
from tests.notary.conftest import SECOND, record_row, register

T = 1_791_450_000


def confirmed_batch(
    catalog: Catalog, root: str, leaves: list[tuple[str, int, str]], block_time_s: int
) -> None:
    """leaves: (record_id, bar_close_s, symbol); one batch, confirmed at `block_time_s`."""
    for record_id, bar_close, symbol in leaves:
        row = record_row(record_id, bar_close)
        row["symbol"] = symbol
        register(catalog, row)
    tables.append_rows(
        tables.leaves_table(catalog),
        [
            {
                "bar_close_time_ns": bar_close * SECOND,
                "batch_root": root,
                "ordinal": i,
                "record_id": record_id,
                "record_hash": "11" * 32,
            }
            for i, (record_id, bar_close, _s) in enumerate(leaves)
        ],
    )
    closes = [bar_close * SECOND for _id, bar_close, _s in leaves]
    tables.append_rows(
        tables.batches_table(catalog),
        [
            {
                "max_bar_close_time_ns": max(closes),
                "batch_root": root,
                "leaf_count": len(leaves),
                "min_bar_close_time_ns": min(closes),
                "formed_at_ns": 1,
                "window_ns": 0,
            }
        ],
    )
    tables.append_rows(
        tables.events_table(catalog),
        [
            tables.event_row(root, "formed", at_ns=1),
            tables.event_row(
                root, "confirmed", at_ns=2, block_number=1, block_time_s=block_time_s, tx_hash="0x1"
            ),
        ],
    )


@pytest.mark.trace("REQ-INFRA-007")
def test_latency_is_per_record_from_its_own_bar_close_not_per_batch(catalog: Catalog) -> None:
    confirmed_batch(
        catalog,
        "aa" * 32,
        [("a", T, "BTCUSDT"), ("b", T + 600, "ETHUSDT"), ("c", T + 1200, "SOLUSDT")],
        block_time_s=T + 2000,
    )
    report = latency_report(catalog, since_s=0)

    assert report.sample == 3
    assert sorted(report.latencies_s) == [800, 1400, 2000]
    assert (report.median_s, report.max_s) == (1400, 2000)
    assert report.series == 3


@pytest.mark.trace("REQ-INFRA-007")
def test_the_percentile_is_nearest_rank_and_never_interpolated(catalog: Catalog) -> None:
    leaves = [(f"r{i:02d}", T + i, "BTCUSDT") for i in range(100)]
    confirmed_batch(catalog, "bb" * 32, leaves, block_time_s=T + 1000)
    report = latency_report(catalog, since_s=0)

    ordered = sorted(1000 - i for i in range(100))
    assert report.p95_s == ordered[94]  # the 95th of 100 values: a latency that actually happened
    assert report.sample == 100


@pytest.mark.trace("REQ-INFRA-007")
def test_a_sample_below_the_success_criterion_is_labelled_insufficient_not_reported_as_a_result(
    catalog: Catalog,
) -> None:
    confirmed_batch(
        catalog,
        "cc" * 32,
        [("a", T, "BTCUSDT"), ("b", T + 60, "ETHUSDT")],
        block_time_s=T + 600,
    )
    report = latency_report(catalog, since_s=0)

    assert not report.meets_criterion  # fewer than 50 records, fewer than 3 series, under an hour
    assert "insufficient" in report.verdict


@pytest.mark.trace("REQ-INFRA-007")
def test_a_sample_that_meets_the_criterion_says_so(catalog: Catalog) -> None:
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    leaves = [(f"r{i:03d}", T + i * 90, symbols[i % 3]) for i in range(60)]
    confirmed_batch(catalog, "dd" * 32, leaves, block_time_s=T + 60 * 90 + 600)
    # A second batch an hour and more later gives the window its length.
    confirmed_batch(
        catalog, "ee" * 32, [("late", T + 3 * 3600, "BTCUSDT")], block_time_s=T + 3 * 3600 + 900
    )
    report = latency_report(catalog, since_s=0)

    assert report.sample == 61 and report.series == 3 and report.window_s >= 3600
    assert report.meets_criterion and "meets" in report.verdict


@pytest.mark.trace("REQ-INFRA-007")
def test_only_confirmed_batches_count_and_the_window_filters_by_the_chains_time(
    catalog: Catalog,
) -> None:
    confirmed_batch(catalog, "ff" * 32, [("old", T, "BTCUSDT")], block_time_s=T + 100)
    confirmed_batch(catalog, "11" * 32, [("new", T + 5000, "BTCUSDT")], block_time_s=T + 5100)
    # A batch that never confirmed contributes nothing.
    register(catalog, record_row("unsent", T + 9000))
    tables.append_rows(
        tables.leaves_table(catalog),
        [
            {
                "bar_close_time_ns": (T + 9000) * SECOND,
                "batch_root": "22" * 32,
                "ordinal": 0,
                "record_id": "unsent",
                "record_hash": "11" * 32,
            }
        ],
    )
    tables.append_rows(
        tables.batches_table(catalog),
        [
            {
                "max_bar_close_time_ns": (T + 9000) * SECOND,
                "batch_root": "22" * 32,
                "leaf_count": 1,
                "min_bar_close_time_ns": (T + 9000) * SECOND,
                "formed_at_ns": 1,
                "window_ns": 0,
            }
        ],
    )
    tables.append_rows(
        tables.events_table(catalog), [tables.event_row("22" * 32, "failed", at_ns=3)]
    )

    everything = latency_report(catalog, since_s=0)
    recent = latency_report(catalog, since_s=T + 1000)

    assert everything.sample == 2 and recent.sample == 1 and recent.latencies_s == [100]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_latency_command_prints_the_report_as_json(
    catalog: Catalog, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    from channelflow.notary import latency as cli

    confirmed_batch(
        catalog, "ab" * 32, [("a", T, "BTCUSDT"), ("b", T + 60, "ETHUSDT")], block_time_s=T + 600
    )
    assert cli.main(["--since", "0"], catalog=catalog) == 0
    printed = json.loads(capsys.readouterr().out)
    assert (
        printed["sample"] == 2 and printed["max_s"] == 600 and printed["meets_criterion"] is False
    )
    assert "insufficient" in printed["verdict"] and "latencies_s" not in printed
