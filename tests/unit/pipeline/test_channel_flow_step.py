"""The worker pass writes the flow rows from the bars it already reads (REQ-WP-088).

`test_channel_main.py` replaces module attributes of `channel_main` for good (no monkeypatch),
so this file sets the ones it depends on itself, to known values, and does not trust what an
earlier test left there.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from channelflow.pipeline import channel_main
from channelflow.tables import bars as real_bars
from channelflow.tables import features as features_table
from channelflow.timeframes import TIMEFRAMES

from ..features.test_flow_bars import make_bar


def _stub_replay() -> MagicMock:
    return MagicMock(
        return_value=(
            MagicMock(channel_snapshots=0, signals=0, confirmed_extrema=0, extremum_candidates=0),
            MagicMock(),
        )
    )


def _seed(catalog, count: int) -> None:
    sink = real_bars.BarSink(table=real_bars.table_for(catalog))
    for i in range(count):
        sink(make_bar(i, str(i + 3), str(7 - i)))
    sink.flush()


def _flow_times(catalog) -> list[int]:
    rows = features_table.features_table_for(catalog).read().to_pylist()
    return sorted(r["at_ns"] for r in rows if r["feature_name"] == "cvd_base")


def _patched(monkeypatch, replay) -> None:
    monkeypatch.setattr(channel_main, "bars_table", real_bars)
    monkeypatch.setattr(channel_main, "record_replay", replay)


@pytest.mark.trace("REQ-WP-088")
def test_a_pass_writes_the_flow_rows_and_a_second_pass_writes_nothing(catalog, monkeypatch) -> None:
    _patched(monkeypatch, _stub_replay())
    _seed(catalog, 5)
    targets = [TIMEFRAMES["1m"]]

    channel_main.run_pass(catalog, targets=targets)
    after_first = _flow_times(catalog)
    channel_main.run_pass(catalog, targets=targets)

    assert len(after_first) == 5
    assert _flow_times(catalog) == after_first


@pytest.mark.trace("REQ-WP-088")
def test_the_flow_step_writes_every_timeframe_the_bars_table_has(catalog, monkeypatch) -> None:
    """Flow comes from each timeframe's own stored bars, including those `resample` builds."""
    _patched(monkeypatch, _stub_replay())
    sink = real_bars.BarSink(table=real_bars.table_for(catalog))
    quarter = TIMEFRAMES["15m"].ns
    for i in range(2):
        sink(make_bar(i, "5", "3"))
        sink(make_bar(i, "50", "30", ids=(i * 150 + 1, i * 150 + 150), timeframe_ns=quarter))
    sink.flush()

    channel_main.run_pass(catalog, targets=[TIMEFRAMES["1m"]])

    rows = features_table.features_table_for(catalog).read().to_pylist()
    timeframes = {r["timeframe_ns"] for r in rows if r["feature_name"] == "cvd_base"}
    assert timeframes == {TIMEFRAMES["1m"].ns, quarter}


@pytest.mark.trace("REQ-WP-088")
def test_the_channel_step_still_gets_the_bars_it_always_got(catalog, monkeypatch) -> None:
    replay = _stub_replay()
    _patched(monkeypatch, replay)
    _seed(catalog, 3)

    channel_main.run_pass(catalog, targets=[TIMEFRAMES["1m"]])

    assert len(replay.call_args.kwargs["bars"]) == 3
    assert replay.call_args.kwargs["timeframe_ns"] == TIMEFRAMES["1m"].ns


@pytest.mark.trace("REQ-WP-088")
def test_a_failing_flow_step_does_not_stop_the_channel_step(catalog, monkeypatch, capsys) -> None:
    """One feature step failing must not end the series' channel work, nor the pass."""
    replay = _stub_replay()
    _patched(monkeypatch, replay)
    monkeypatch.setattr(channel_main, "write_flow", MagicMock(side_effect=RuntimeError("boom")))
    _seed(catalog, 3)

    results = channel_main.run_pass(catalog, targets=[TIMEFRAMES["1m"]])

    assert results
    assert replay.called
    assert "flow step failed" in capsys.readouterr().out
