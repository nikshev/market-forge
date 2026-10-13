"""What of the live chart can be checked without Node (REQ-WP-102).

# @trace: REQ-WP-102

The behaviour of the page -- the merge rules, the socket's lifecycle, the in-place update of the
candle, the panes' axis, the live/delayed chip -- is tested by vitest (`make web-test`), which runs
only in CI (ADR-021). A vitest test cannot carry a pytest marker, so this is the part the fast gate
can see for itself: the modules carry their `@trace`, each vitest file that covers the feed names
the requirement, and the page wires the one hook into the chart, the pane and the chip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "src"

MODULES = ("live.ts", "useLiveBars.ts", "LiveChip.tsx", "Chart.tsx", "PaneChart.tsx", "App.tsx")
VITEST = ("live.test.ts", "useLiveBars.test.tsx", "chartLive.test.tsx", "appLive.test.tsx")


@pytest.mark.trace("REQ-WP-102")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "@trace: REQ-WP-102" in (WEB / module).read_text()


@pytest.mark.trace("REQ-WP-102")
@pytest.mark.parametrize("name", VITEST)
def test_each_vitest_file_for_the_feed_exists_and_names_the_requirement(name: str) -> None:
    path = WEB / "__tests__" / name

    assert path.is_file(), f"{path.name} is missing"
    assert "@trace: REQ-WP-102" in path.read_text()


@pytest.mark.trace("REQ-WP-102")
def test_the_page_gives_the_one_feed_to_the_chart_the_pane_and_the_chip() -> None:
    app = (WEB / "App.tsx").read_text()

    assert "useLiveBars(" in app
    assert "liveBars={live.bars}" in app and app.count("liveBars={live.bars}") == 2
    assert "<LiveChip status={live.status} />" in app


@pytest.mark.trace("REQ-WP-102")
def test_the_feed_is_asked_for_only_by_the_one_minute_unpinned_view() -> None:
    app = (WEB / "App.tsx").read_text()

    assert "link.atNs === null" in app and "option.token === LIVE_TIMEFRAME" in app


@pytest.mark.trace("REQ-WP-102")
def test_the_socket_goes_to_the_gated_path_under_the_one_proxied_prefix() -> None:
    live = (WEB / "live.ts").read_text()

    assert 'LIVE_PATH = "/api/v1/live"' in live
