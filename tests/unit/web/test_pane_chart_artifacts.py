"""What of the lower pane chart can be checked without Node (REQ-WP-092).

# @trace: REQ-WP-092

The behaviour -- the alignment of values to bars, the synchronisation of the two charts, the
series per run, the fallback -- is tested by vitest (`make web-test`), which runs only in CI:
ADR-021 keeps Node out of the commit hook. A vitest test cannot carry a pytest marker, so this file
is the part the fast gate can see for itself: the eight live screenshots exist (Volume and CVD,
light and dark, 1280 px and 390 px) and the modules carry their `@trace`. It does not look at the
screenshots or measure the alignment; that was done in a browser and the outcome note records it.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
SHOTS = ROOT / "docs" / "ui"

PANES = ("volume", "cvd")
SCHEMES = ("light", "dark")
SIZES = {"desktop": 1280, "phone": 390}
MODULES = ("paneChart.ts", "PaneChart.tsx", "Chart.tsx", "FlowPane.tsx", "App.tsx")


@pytest.mark.trace("REQ-WP-092")
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("pane", PANES)
def test_there_is_a_live_screenshot_of_each_pane_in_each_scheme_at_each_width(
    pane: str, scheme: str, size: str
) -> None:
    path = SHOTS / f"pane-{pane}-{scheme}-{size}.png"

    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24])[0] == SIZES[size]


@pytest.mark.trace("REQ-WP-092")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "// @trace: REQ-WP-092" in (WEB / "src" / module).read_text()
