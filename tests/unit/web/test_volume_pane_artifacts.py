"""What of the volume pane can be checked without Node (REQ-WP-085).

# @trace: REQ-WP-085

The behaviour -- the volume series, the pane row, the availability rules, the drawing -- is
tested by vitest (`make web-test`), which runs only in CI: ADR-021 keeps Node out of the commit
hook. A vitest test cannot carry a pytest marker, so this file is the part the fast gate can see
for itself, and it is only that part: the two live screenshots FR-008 asks for exist, and the
modules carry their `@trace`. It does not look at the screenshots; that was done by eye and the
outcome note records what it found.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
SHOTS = ROOT / "docs" / "ui"

MODULES = ("panes.ts", "FlowPane.tsx", "App.tsx")


@pytest.mark.trace("REQ-WP-085")
@pytest.mark.parametrize("scheme", ("light", "dark"))
def test_there_is_a_live_screenshot_of_the_volume_pane_in_each_scheme(scheme: str) -> None:
    path = SHOTS / f"volume-pane-{scheme}.png"

    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24])[0] > 300


@pytest.mark.trace("REQ-WP-085")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "// @trace: REQ-WP-085" in (WEB / "src" / module).read_text()
