"""Dump which tests claim which requirements, straight from pytest's collection.

Reading markers from collection rather than from source means parametrized and
dynamically generated tests are counted individually and correctly.

Usage:
    pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json --collect-only -q
"""
# @trace: REQ-INFRA-001

from __future__ import annotations

import json
from pathlib import Path


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--trace-dump",
        action="store",
        default=None,
        metavar="PATH",
        help="Write collected @pytest.mark.trace requirement links to this JSON file.",
    )


def pytest_collection_finish(session) -> None:
    destination = session.config.getoption("--trace-dump")
    if not destination:
        return

    entries = []
    for item in session.items:
        requirements: list[str] = []
        for marker in item.iter_markers(name="trace"):
            requirements.extend(str(arg) for arg in marker.args)
        if requirements:
            entries.append(
                {"nodeid": item.nodeid, "requirements": list(dict.fromkeys(requirements))}
            )

    entries.sort(key=lambda entry: entry["nodeid"])
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
