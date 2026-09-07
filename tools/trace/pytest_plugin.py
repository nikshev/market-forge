"""Dump which tests VERIFY which requirements — meaning the test actually
passed, not merely that it was collected.

Reading markers from collection rather than from source means parametrized
and dynamically generated tests are counted individually and correctly. But
collection alone cannot tell a genuinely passing test from one that is
skipped, xfailed, or never run — so this plugin also watches run outcomes
(`pytest_runtest_logreport`) and writes an entry only for a test that both
carries `@pytest.mark.trace(...)` and passed outright (not `xfail`/`xpass`)
the last time it actually ran.

Under `--collect-only` no test runs at all, so no outcome is knowable; the
dump is written empty in that mode rather than guessing. This means
`--collect-only` is no longer useful for populating `.trace/tests.json` for
real — `make markers` now runs the suite for real for exactly this reason.

Usage:
    pytest -p tools.trace.pytest_plugin --trace-dump=.trace/tests.json -q
"""
# @trace: REQ-INFRA-001

from __future__ import annotations

import json
from pathlib import Path

# One frame per active pytest session, pushed at pytest_configure and popped
# at pytest_unconfigure. A session's own tests may themselves run pytest
# in-process (this plugin's own test suite does exactly that, via pytester),
# so sessions can nest; the stack ensures each nested run's collection and
# outcomes land in its own frame instead of clobbering the outer session's,
# and pytest_runtest_logreport (which pytest calls with only a report, no
# session/config) always finds the right frame by using whichever is
# innermost/currently running.
_SESSIONS: list[dict] = []


def pytest_addoption(parser) -> None:
    parser.addoption(
        "--trace-dump",
        action="store",
        default=None,
        metavar="PATH",
        help="Write requirement links for tests that passed to this JSON file.",
    )


def pytest_configure(config) -> None:
    _SESSIONS.append({"config": config, "collected": {}, "passed": set()})


def pytest_unconfigure(config) -> None:
    for index in range(len(_SESSIONS) - 1, -1, -1):
        if _SESSIONS[index]["config"] is config:
            del _SESSIONS[index]
            return


def _frame_for(config) -> dict | None:
    for frame in reversed(_SESSIONS):
        if frame["config"] is config:
            return frame
    return None


def pytest_collection_finish(session) -> None:
    frame = _frame_for(session.config)
    if frame is None:
        return
    for item in session.items:
        requirements: list[str] = []
        for marker in item.iter_markers(name="trace"):
            requirements.extend(str(arg) for arg in marker.args)
        if requirements:
            frame["collected"][item.nodeid] = list(dict.fromkeys(requirements))


def pytest_runtest_logreport(report) -> None:
    """Record the call-phase outcome for the innermost active session.

    `wasxfail` is set by pytest on both xfail (outcome "skipped") and xpass
    (outcome "passed", unless strict) reports; either way that test was not
    a plain, unconditional pass, so it must not count as verifying.
    """
    if report.when != "call" or not _SESSIONS:
        return
    if report.outcome == "passed" and getattr(report, "wasxfail", None) is None:
        _SESSIONS[-1]["passed"].add(report.nodeid)


def pytest_sessionfinish(session) -> None:
    frame = _frame_for(session.config)
    if frame is None:
        return
    destination = session.config.getoption("--trace-dump")
    if not destination:
        return

    collect_only = bool(session.config.getoption("--collect-only"))

    entries = []
    if not collect_only:
        for nodeid, requirements in frame["collected"].items():
            if nodeid in frame["passed"]:
                entries.append({"nodeid": nodeid, "requirements": requirements})

    entries.sort(key=lambda entry: entry["nodeid"])
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n")
