"""What of the chart's opening view can be checked without Node (REQ-WP-108).

# @trace: REQ-WP-108

The behaviour is tested by vitest (`make web-test`), which runs only in CI (ADR-021): a vitest test
cannot carry a pytest marker, so this is the part the fast gate can see for itself -- the modules
name the requirement, the chart opens through `recentRange` rather than on the whole history, and
the vitest file exists.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "src"

pytestmark = pytest.mark.trace("REQ-WP-108")


@pytest.mark.parametrize("module", ["Chart.tsx", "series.ts"])
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "@trace: REQ-WP-108" in (WEB / module).read_text()


def test_the_chart_opens_on_the_newest_bars_not_on_the_whole_history() -> None:
    source = (WEB / "Chart.tsx").read_text()

    assert "recentRange(" in source
    assert "PROFILE_ROOM" in source


def test_the_number_of_bars_shown_is_small_enough_for_the_last_bar_to_be_seen() -> None:
    match = re.search(r"export const RECENT_BARS = (\d+);", (WEB / "series.ts").read_text())

    assert match is not None and int(match.group(1)) <= 200


def test_the_behaviour_is_covered_by_a_vitest_file_that_names_the_requirement() -> None:
    test = WEB / "__tests__" / "liveView.test.ts"

    assert test.is_file()
    assert "@trace: REQ-WP-108" in test.read_text()
