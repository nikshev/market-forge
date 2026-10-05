# @trace: REQ-WP-090
"""
Test that modules modified for REQ-WP-090 carry trace markers.
"""

import pathlib

import pytest

TRACE_COMMENT_PY = "# @trace: REQ-WP-090"
TRACE_COMMENT_TS = "// @trace: REQ-WP-090"


def collect_py_files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in root.rglob("*.py") if "test" not in str(p) and "__pycache__" not in str(p)]


def collect_ts_files(root: pathlib.Path) -> list[pathlib.Path]:
    return [
        p
        for p in root.rglob("*.ts*")
        if "test" not in str(p) and "node_modules" not in str(p) and ".d.ts" not in str(p)
    ]


def has_trace_marker_py(filepath: pathlib.Path) -> bool:
    try:
        content = filepath.read_text()
        return TRACE_COMMENT_PY in content
    except Exception:
        return False


def has_trace_marker_ts(filepath: pathlib.Path) -> bool:
    try:
        content = filepath.read_text()
        return TRACE_COMMENT_TS in content
    except Exception:
        return False


# Files expected to be modified for REQ-WP-090 (from tasks.md coverage)
EXPECTED_PY_FILES = [
    "src/channelflow/api/lakehouse_repository.py",  # stage 1 is web-only
]

EXPECTED_TS_FILES = [
    "apps/web/src/App.tsx",
    "apps/web/src/Chart.tsx",
    "apps/web/src/.env.example",  # not a source file, skip
    "apps/web/src/vite.config.ts",
]


@pytest.mark.trace("REQ-WP-090")
def test_python_modules_carry_trace_marker():
    """Python modules touched by REQ-WP-090 carry the trace marker."""
    repo_root = pathlib.Path(__file__).parent.parent.parent
    for rel_path in EXPECTED_PY_FILES:
        filepath = repo_root / rel_path
        if filepath.exists():
            assert has_trace_marker_py(filepath), f"{rel_path} missing {TRACE_COMMENT_PY}"


@pytest.mark.trace("REQ-WP-090")
def test_typescript_modules_carry_trace_marker():
    """TypeScript/TSX modules touched by REQ-WP-090 carry the trace marker."""
    repo_root = pathlib.Path(__file__).parent.parent.parent
    for rel_path in EXPECTED_TS_FILES:
        filepath = repo_root / rel_path
        if filepath.exists() and filepath.suffix in (".ts", ".tsx"):
            assert has_trace_marker_ts(filepath), f"{rel_path} missing {TRACE_COMMENT_TS}"
