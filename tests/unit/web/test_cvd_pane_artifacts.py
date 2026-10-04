"""What of the CVD (base) pane can be checked without Node (REQ-WP-088).

# @trace: REQ-WP-088

The behaviour -- the pane's line, its break at a `cvd_run` change, "no data" without rows -- is
tested by vitest (`make web-test`), which runs only in CI: ADR-021 keeps Node out of the commit
hook. A vitest test cannot carry a pytest marker, so this file is the part the fast gate can see
for itself: the two live screenshots exist, the modules carry their `@trace`, and the pane list
names the feature the worker writes. It does not look at the screenshots; that was done by eye and
the outcome note records what it found.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from channelflow.features.flow_bars import FLOW_FEATURES

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
SHOTS = ROOT / "docs" / "ui"

MODULES = ("panes.ts", "FlowPane.tsx")


@pytest.mark.trace("REQ-WP-088")
@pytest.mark.parametrize("scheme", ("light", "dark"))
def test_there_is_a_live_screenshot_of_the_cvd_pane_in_each_scheme(scheme: str) -> None:
    path = SHOTS / f"cvd-pane-{scheme}.png"

    assert path.is_file(), f"{path.relative_to(ROOT)} is missing"
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", header[16:24])[0] > 300


@pytest.mark.trace("REQ-WP-088")
@pytest.mark.parametrize("module", MODULES)
def test_every_module_this_requirement_touches_names_it(module: str) -> None:
    assert "// @trace: REQ-WP-088" in (WEB / "src" / module).read_text()


@pytest.mark.trace("REQ-WP-088")
def test_the_cvd_pane_names_a_feature_the_worker_writes() -> None:
    """The pane's feature and the producer's names are two halves; neither can check itself."""
    source = (WEB / "src" / "panes.ts").read_text()

    assert re.search(r'feature: "cvd_base", label: "CVD \(base\)"', source)
    assert "cvd_base" in FLOW_FEATURES
