"""The pane report decides a pane's state from the API's answers, offline (REQ-WP-097, spec 149)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools.panes import __main__ as report
from tools.panes.classify import (
    ABSENT,
    DATA,
    NO_PRODUCER,
    Evidence,
    classify,
    count_features,
)
from tools.panes.fetch import ApiUnreachable, panes_from_page

NS = 1_000_000_000


def evidence(
    counts: dict[str, int] | None = None,
    *,
    bars: int = 10,
    consensus: list[str] | None = None,
    error: str | None = None,
) -> Evidence:
    return Evidence(counts or {}, bars, consensus, error)


# --- the three states ---


@pytest.mark.trace("REQ-WP-097")
def test_a_pane_with_a_point_is_data() -> None:
    assert classify("open_interest_usd", evidence({"open_interest_usd": 3})).state == DATA


@pytest.mark.trace("REQ-WP-097")
def test_a_pane_with_no_point_and_no_reason_is_no_producer() -> None:
    state = classify("open_interest_usd", evidence({"cvd_base": 100}))
    assert state.state == NO_PRODUCER


@pytest.mark.trace("REQ-WP-097")
def test_volume_is_read_from_the_bars_not_from_a_feature() -> None:
    assert classify("volume", evidence(bars=5)).state == DATA
    assert classify("volume", evidence(bars=0)).state == NO_PRODUCER


@pytest.mark.trace("REQ-WP-097")
def test_the_dex_panes_are_absent_with_the_one_reason_the_module_states() -> None:
    for feature in ("dex_swap_imbalance", "dex_active_liquidity"):
        state = classify(feature, evidence())
        assert state.state == ABSENT and "no DEX source" in state.reason


@pytest.mark.trace("REQ-WP-097")
def test_a_dex_pane_that_has_data_is_data_whatever_the_deployment_says() -> None:
    assert classify("dex_swap_imbalance", evidence({"dex_swap_imbalance": 1})).state == DATA


# --- reasons come from the system ---


@pytest.mark.trace("REQ-WP-097")
def test_venue_basis_with_a_stored_refusal_is_absent_with_the_stored_reason() -> None:
    reason = "only 1 venue(s) could contribute at 5; a median over one venue is that venue's mid"
    state = classify("venue_basis_bps", evidence(consensus=[reason, reason]))

    assert state.state == ABSENT and state.reason == reason  # the same reason, once


@pytest.mark.trace("REQ-WP-097")
def test_venue_basis_whose_consensus_read_failed_is_no_producer_and_says_what_it_answered() -> None:
    state = classify("venue_basis_bps", evidence(error="HTTP 404 no consensus for okx X in 24h"))

    assert state.state == NO_PRODUCER and "HTTP 404" in state.reason


@pytest.mark.trace("REQ-WP-097")
def test_venue_basis_with_consensus_rows_but_no_basis_is_no_producer_not_absent() -> None:
    assert classify("venue_basis_bps", evidence(consensus=[])).state == NO_PRODUCER


@pytest.mark.trace("REQ-WP-097")
def test_liquidations_with_covered_windows_and_no_event_are_absent_for_a_true_reason() -> None:
    state = classify("liquidation_imbalance_5m", evidence({"liquidation_long_usd_5m": 120}))

    assert state.state == ABSENT
    assert "stream was listening" in state.reason and "120" in state.reason


@pytest.mark.trace("REQ-WP-097")
def test_liquidations_with_no_covered_window_are_no_producer() -> None:
    state = classify("liquidation_imbalance_5m", evidence({}))
    assert state.state == NO_PRODUCER and "heartbeat" in state.reason


@pytest.mark.trace("REQ-WP-097")
def test_the_imbalance_having_points_is_data_even_with_no_sums() -> None:
    assert (
        classify("liquidation_imbalance_5m", evidence({"liquidation_imbalance_5m": 2})).state
        == DATA
    )


# --- counting ---


@pytest.mark.trace("REQ-WP-097")
def test_only_real_numbers_count_as_a_value() -> None:
    points = [
        {"at_ns": "1", "values": {"a": 1.0, "b": None, "c": "x", "d": True}},
        {"at_ns": "2", "values": {"a": 0, "e": 2.5}},
        {"at_ns": "3", "values": {}},
        {"at_ns": "4"},
    ]
    assert count_features(points) == {
        "a": 2,
        "e": 1,
    }  # zero is a reading; None, text and bools are not


# --- the page's own list of panes ---


@pytest.mark.trace("REQ-WP-097")
def test_the_panes_are_read_from_the_page_with_volume_first() -> None:
    panes = panes_from_page()
    assert panes[0][0] == "volume"
    names = [name for name, _ in panes]
    assert {
        "cvd_base",
        "ofi_1m",
        "open_interest_usd",
        "venue_basis_bps",
        "dex_swap_imbalance",
    } <= set(names)
    assert len(names) == len(set(names))


@pytest.mark.trace("REQ-WP-097")
def test_a_page_with_no_panes_is_an_error_not_an_empty_report(tmp_path: Path) -> None:
    empty = tmp_path / "panes.ts"
    empty.write_text("export const nothing = [];\n")
    with pytest.raises(ValueError, match="no pane found"):
        panes_from_page(empty)


# --- the report and its exit codes ---


def fake_api(*, features: dict[str, int], consensus: tuple[int, Any], bars: int = 5) -> Any:
    calls: list[tuple[str, dict[str, str]]] = []

    def get(path: str, params: dict[str, str]) -> tuple[int, Any]:
        calls.append((path, params))
        if path == "/api/v1/markets":
            return 200, {
                "markets": [{"venue": "bybit", "symbol": "BTCUSDT", "market_type": "perp"}]
            }
        if path == "/api/v1/timeframes":
            return 200, {
                "timeframes": [
                    {"token": "1m", "timeframe_ns": 60 * NS},
                    {"token": "1h", "timeframe_ns": 3600 * NS},
                ]
            }
        if path == "/api/v1/features/timeseries":
            return 200, {
                "points": [{"at_ns": "1", "values": {k: 1.0 for k, n in features.items() if n}}]
            }
        if path == "/api/v1/bars":
            return 200, {"bars": [{}] * bars}
        if path == "/api/v1/consensus":
            return consensus
        return 404, None

    get.calls = calls  # type: ignore[attr-defined]
    return get


@pytest.mark.trace("REQ-WP-097")
def test_every_cell_data_or_reasoned_exits_zero() -> None:
    panes = panes_from_page()
    all_features = {name: 1 for name, _ in panes if name != "volume"}
    get = fake_api(features=all_features, consensus=(200, {"consensus": []}))

    lines, failed = report.run(get, panes=panes, hours=24, now_ns=10**18, only_timeframes=["1m"])

    assert not failed
    assert any("Volume" in line and "data" in line for line in lines)
    assert report.main(["--timeframes", "1m"], get=get) == 0


@pytest.mark.trace("REQ-WP-097")
def test_a_cell_with_no_producer_makes_the_report_fail_and_names_the_pane() -> None:
    panes = panes_from_page()
    get = fake_api(features={"cvd_base": 1}, consensus=(404, {"detail": "no consensus"}))

    lines, failed = report.run(get, panes=panes, hours=24, now_ns=10**18, only_timeframes=["1m"])

    assert failed
    assert any("Open interest" in line and "no-producer" in line for line in lines)
    assert report.main(["--timeframes", "1m"], get=get) == 1


@pytest.mark.trace("REQ-WP-097")
def test_every_market_and_every_chosen_timeframe_is_queried_and_none_is_invented() -> None:
    panes = panes_from_page()
    get = fake_api(features={}, consensus=(404, {}))

    lines, _ = report.run(get, panes=panes, hours=24, now_ns=10**18, only_timeframes=None)

    headings = [line for line in lines if not line.startswith(" ")]
    assert headings == ["bybit BTCUSDT (perp) 1m", "bybit BTCUSDT (perp) 1h"]


@pytest.mark.trace("REQ-WP-097")
def test_the_range_asked_for_ends_now_and_starts_the_stated_hours_before() -> None:
    get = fake_api(features={}, consensus=(404, {}))
    report.run(
        get, panes=[("volume", "Volume")], hours=6, now_ns=100 * 3600 * NS, only_timeframes=["1m"]
    )

    asked = [p for path, p in get.calls if path == "/api/v1/features/timeseries"][0]
    assert int(asked["end_ns"]) == 100 * 3600 * NS
    assert int(asked["end_ns"]) - int(asked["start_ns"]) == 6 * 3600 * NS


@pytest.mark.trace("REQ-WP-097")
def test_an_api_that_cannot_be_reached_exits_two_and_prints_no_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def down(path: str, params: dict[str, str]) -> tuple[int, Any]:
        raise ApiUnreachable("connection refused")

    assert report.main([], get=down) == 2
    captured = capsys.readouterr()
    assert "could not be read" in captured.err and captured.out == ""


@pytest.mark.trace("REQ-WP-097")
def test_an_api_that_answers_the_markets_read_with_an_error_is_unreachable_not_an_empty_table() -> (
    None
):
    def broken(path: str, params: dict[str, str]) -> tuple[int, Any]:
        return 500, None

    assert report.main([], get=broken) == 2


@pytest.mark.trace("REQ-WP-097")
def test_a_refused_consensus_is_reported_as_the_reason_the_api_stored() -> None:
    reason = "only 1 venue(s) could contribute"
    get = fake_api(
        features={},
        consensus=(200, {"consensus": [{"refusal_reason": reason, "consensus_mid": None}]}),
    )

    lines, _ = report.run(
        get,
        panes=[("venue_basis_bps", "Venue basis (bps)")],
        hours=24,
        now_ns=10**18,
        only_timeframes=["1m"],
    )

    assert any(f"absent: {reason}" in line for line in lines)


@pytest.mark.trace("REQ-WP-097")
def test_only_the_chosen_timeframes_are_queried() -> None:
    get = fake_api(features={}, consensus=(404, {}))
    lines, _ = report.run(
        get, panes=[("volume", "Volume")], hours=24, now_ns=10**18, only_timeframes=["1m"]
    )
    assert [line for line in lines if not line.startswith(" ")] == ["bybit BTCUSDT (perp) 1m"]


@pytest.mark.trace("REQ-WP-097")
def test_a_markets_read_that_fails_is_unreachable_even_if_the_other_reads_answer() -> None:
    def only_markets_fail(path: str, params: dict[str, str]) -> tuple[int, Any]:
        if path == "/api/v1/markets":
            return 503, None
        return 200, {"timeframes": [{"token": "1m", "timeframe_ns": 60 * NS}]}

    with pytest.raises(ApiUnreachable, match="markets"):
        report.run(only_markets_fail, panes=[("volume", "Volume")], hours=1, now_ns=10**18)
