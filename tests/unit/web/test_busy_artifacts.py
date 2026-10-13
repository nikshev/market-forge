"""What of the loading indicators can be checked without Node (REQ-WP-103).

# @trace: REQ-WP-103

The behaviour -- a spinner while a request is outstanding, gone when it answers whatever the
answer is, none where nothing is waiting -- is tested by vitest (`make web-test`), which runs only
in CI (ADR-021). This is the part the fast gate can see for itself: the modules carry their
`@trace`, the one component is a `progressbar` and never a `status`, every place the page waits uses
it, and the page shows something before the script has even loaded.
"""

from __future__ import annotations

from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[3] / "apps" / "web"
SRC = WEB / "src"

MODULES = (
    "Busy.tsx",
    "LiveChip.tsx",
    "Markets.tsx",
    "ProfileControls.tsx",
    "FlowPane.tsx",
    "App.tsx",
)


@pytest.mark.trace("REQ-WP-103")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "@trace: REQ-WP-103" in (SRC / module).read_text()


@pytest.mark.trace("REQ-WP-103")
def test_the_spinner_is_a_progress_bar_and_never_a_status() -> None:
    busy = (SRC / "Busy.tsx").read_text()

    assert "CircularProgress" in busy and "aria-label={label}" in busy
    assert 'role="status"' not in busy


@pytest.mark.trace("REQ-WP-103")
@pytest.mark.parametrize(
    ("module", "label"),
    [
        ("Markets.tsx", "Loading markets"),
        ("Markets.tsx", "Loading timeframes"),
        ("App.tsx", "Loading timeframes"),
        ("App.tsx", "Loading the chart"),
        ("App.tsx", "Updating the chart"),
        ("App.tsx", "Loading the consensus"),
        ("FlowPane.tsx", "Loading the pane"),
        ("ProfileControls.tsx", "Loading the volume profile"),
    ],
)
def test_every_place_the_page_waits_has_a_named_spinner(module: str, label: str) -> None:
    assert f'label="{label}"' in (SRC / module).read_text()


@pytest.mark.trace("REQ-WP-103")
def test_the_live_chip_shows_a_spinner_while_it_connects_and_not_the_word_delayed() -> None:
    chip = (SRC / "LiveChip.tsx").read_text()

    assert 'status === "connecting"' in chip and "Connecting to the live feed" in chip


@pytest.mark.trace("REQ-WP-103")
def test_the_page_shows_something_before_the_script_has_loaded() -> None:
    html = (WEB / "index.html").read_text()

    root = html[html.index('<div id="root">') :]
    assert 'role="progressbar"' in root.split("</div>")[0] + "</div>"
    assert "boot-spin" in html


@pytest.mark.trace("REQ-WP-103")
def test_the_behaviour_is_covered_by_vitest_files_that_name_the_requirement() -> None:
    for name in ("busy.test.tsx", "appBusy.test.tsx"):
        path = SRC / "__tests__" / name
        assert path.is_file() and "@trace: REQ-WP-103" in path.read_text()
