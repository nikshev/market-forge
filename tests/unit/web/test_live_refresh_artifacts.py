# @trace: REQ-WP-090
"""
Test that modules modified for REQ-WP-090 carry trace markers.
"""

import pathlib

import pytest


@pytest.mark.trace("REQ-WP-090")
def test_modules_trace():
    """Modules modified for REQ-WP-090 carry trace markers."""
    repo_root = pathlib.Path(__file__).parent.parent.parent

    ts_files = [
        "apps/web/src/App.tsx",
        "apps/web/src/Chart.tsx",
    ]

    for rel_path in ts_files:
        filepath = repo_root / rel_path
        if filepath.exists():
            content = filepath.read_text()
            assert "// @trace: REQ-WP-090" in content, f"{rel_path} missing trace marker"
