"""What of the chart's reading interaction can be checked without Node (REQ-WP-101).

# @trace: REQ-WP-101

The behaviour is tested by vitest (`make web-test`), which runs only in CI (ADR-021): a vitest test
cannot carry a pytest marker, so this is the part the fast gate can see for itself -- the modules
carry their `@trace`, the two charts take their interaction options from the one constant, and that
constant lets a reader scale both axes (the first version switched that off and left a chart that
could not be scaled).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "apps" / "web" / "src"


@pytest.mark.trace("REQ-WP-101")
@pytest.mark.parametrize("module", ["paneChart.ts", "Chart.tsx", "PaneChart.tsx"])
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "@trace: REQ-WP-101" in (WEB / module).read_text()


@pytest.mark.trace("REQ-WP-101")
@pytest.mark.parametrize("module", ["Chart.tsx", "PaneChart.tsx"])
def test_both_charts_are_created_with_the_one_interaction_constant(module: str) -> None:
    source = (WEB / module).read_text()

    assert "handleScroll: CHART_INTERACTION.handleScroll" in source
    assert "handleScale: CHART_INTERACTION.handleScale" in source


@pytest.mark.trace("REQ-WP-101")
def test_the_constant_lets_a_reader_scale_both_axes() -> None:
    source = (WEB / "paneChart.ts").read_text()
    block = source[source.index("export const CHART_INTERACTION") :]
    block = block[: block.index("as const")]

    assert re.search(r"handleScale:\s*{[^}]*mouseWheel:\s*true", block, re.S)
    assert re.search(r"axisPressedMouseMove:\s*{[^}]*price:\s*true", block)
    assert re.search(r"axisDoubleClickReset:\s*{[^}]*price:\s*true", block)
    assert "mouseWheel: false" in block, "the wheel zooms; it does not also scroll the plot"


@pytest.mark.trace("REQ-WP-101")
def test_the_behaviour_is_covered_by_a_vitest_file_that_names_the_requirement() -> None:
    test = WEB / "__tests__" / "readingInteraction.test.tsx"

    assert test.is_file()
    assert "@trace: REQ-WP-101" in test.read_text()
