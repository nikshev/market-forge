"""What of the candidate switch and the pane row can be checked without Node (REQ-WP-084).

# @trace: REQ-WP-084

The behaviour -- the markers handed to the chart, the pane availability, the selection, the roles
and names -- is tested by vitest (`make web-test`), which runs only in CI: ADR-021 keeps Node out
of the commit hook. A vitest test cannot carry a pytest marker, so this file is the part the fast
gate can see for itself, and it is only that part: the eight screenshots FR-010 asks for exist,
and the modules carry their `@trace`. It does not look at the screenshots; that was done by eye
and the outcome note records what it found.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
SHOTS = ROOT / "docs" / "ui"

NAMES = (
    "chart-candidates-off",
    "chart-candidates-on",
    "chart-panes-live-no-data",
    "chart-panes-some-data",
)
SCHEMES = ("light", "dark")

MODULES = ("CandidateSwitch.tsx", "FlowPane.tsx", "panes.ts", "extrema.ts", "Chart.tsx", "App.tsx")


def _png_width(path: Path) -> int:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    return int(struct.unpack(">II", header[16:24])[0])


@pytest.mark.trace("REQ-WP-084")
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("name", NAMES)
def test_there_is_a_screenshot_of_each_state_in_each_scheme(name: str, scheme: str) -> None:
    path = SHOTS / f"{name}-{scheme}.png"

    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    assert _png_width(path) > 300


@pytest.mark.trace("REQ-WP-084")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "// @trace: REQ-WP-084" in (WEB / "src" / module).read_text()
