"""Guards for the two-gate split (REQ-INFRA-002).

No test in this suite can prove a GitHub Actions workflow runs -- that is
verified by observing real runs, recorded in the implement outcome note. What
*is* testable is the local half and the invariant that keeps the split honest,
and those are guarded here.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[3]


def _hook_make_targets() -> set[str]:
    config = yaml.safe_load((REPO / ".pre-commit-config.yaml").read_text())
    targets: set[str] = set()
    for repo in config["repos"]:
        for hook in repo.get("hooks", []):
            match = re.fullmatch(r"make ([a-z-]+)", str(hook.get("entry", "")).strip())
            if match:
                targets.add(match.group(1))
    return targets


def _workflow_make_targets() -> set[str]:
    workflow = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    targets: set[str] = set()
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            targets.update(re.findall(r"\bmake ([a-z-]+)", str(step.get("run", ""))))
    return targets


@pytest.mark.trace("REQ-INFRA-002")
def test_no_check_is_absent_from_both_gates() -> None:
    """FR-009: a check removed from the local hook must run in the workflow.

    This is the invariant that makes the split a trade rather than a loss. It
    was verified by hand once; this makes it a regression guard, so removing a
    step from the workflow while it is also absent from the hook fails here.
    """
    full_gate = {"lint", "typecheck", "test", "validate"}
    local = _hook_make_targets()
    ci = _workflow_make_targets()

    covered_locally = {"lint", "test"} if "test-fast" in local else set()
    missing = full_gate - ci - covered_locally
    assert not missing, (
        f"these checks run in neither gate: {sorted(missing)}. "
        f"hook={sorted(local)} workflow={sorted(ci)}"
    )


@pytest.mark.trace("REQ-INFRA-002")
def test_the_workflow_runs_every_check_of_the_full_gate() -> None:
    """FR-003: the workflow runs lint, type check, the full suite and coverage."""
    ci = _workflow_make_targets()
    for target in ("lint", "typecheck", "test", "validate"):
        assert target in ci, f"the workflow does not run `make {target}`; it runs {sorted(ci)}"


@pytest.mark.trace("REQ-INFRA-002")
def test_the_workflow_runs_the_full_suite_not_the_fast_one() -> None:
    """The workflow must run `make test`, never `make test-fast`.

    Running the fast target in CI would deselect the integration tests in both
    gates at once -- the exact failure FR-009 exists to prevent, and one that
    would look green everywhere.
    """
    assert "test-fast" not in _workflow_make_targets(), (
        "the workflow runs `make test-fast`; integration tests would then run in neither gate"
    )


@pytest.mark.trace("REQ-INFRA-002")
def test_the_fast_gate_deselects_exactly_the_integration_tests() -> None:
    """FR-006/FR-007: the fast gate drops integration tests and nothing else."""

    def collected(*args: str) -> set[str]:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "--no-header", *args],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        return {
            line.strip()
            for line in result.stdout.splitlines()
            if "::" in line and not line.startswith(" ")
        }

    everything = collected()
    fast = collected("-m", "not integration")
    dropped = everything - fast

    assert dropped, "the fast gate deselects nothing; the integration marker is not applied"
    assert all("tests/integration/" in nodeid for nodeid in dropped), (
        f"the fast gate drops non-integration tests: "
        f"{sorted(n for n in dropped if 'tests/integration/' not in n)}"
    )


# --- the light docs gate, and what keeps it honest (REQ-INFRA-002) -----------

CI_WORKFLOW = REPO / ".github/workflows/ci.yml"
DOCS_WORKFLOW = REPO / ".github/workflows/docs.yml"


def _triggers(path: Path) -> dict:
    parsed = yaml.safe_load(path.read_text())
    # PyYAML reads a bare `on:` key as the boolean True.
    return parsed[True] if True in parsed else parsed["on"]


@pytest.mark.trace("REQ-INFRA-002")
def test_the_two_workflows_carve_the_repository_in_two() -> None:
    """Complementary filters, checked rather than maintained in parallel.

    `ci.yml` ignores `docs/**` and `docs.yml` takes exactly it. Two filters that
    can disagree will: widen one and a path runs twice, narrow it and a path
    runs nowhere. The second is the dangerous direction, and it is silent.
    """
    heavy = _triggers(CI_WORKFLOW)
    light = _triggers(DOCS_WORKFLOW)
    for event in ("push", "pull_request"):
        ignored = heavy[event]["paths-ignore"]
        taken = light[event]["paths"]
        assert ignored == taken, (
            f"{event}: ci.yml ignores {ignored} and docs.yml takes {taken}; "
            "a path in neither runs in no gate at all"
        )


@pytest.mark.trace("REQ-INFRA-002")
def test_both_workflows_name_their_job_the_same() -> None:
    """A branch protection rule requires a check by name, and one change runs
    only one of these two. Different names would block every docs-only PR."""
    heavy = yaml.safe_load(CI_WORKFLOW.read_text())["jobs"]
    light = yaml.safe_load(DOCS_WORKFLOW.read_text())["jobs"]
    assert list(heavy) == list(light) == ["gate"]


@pytest.mark.trace("REQ-INFRA-002")
def test_the_light_gate_runs_the_checks_that_need_no_services() -> None:
    """It may skip the stack. It may not skip what costs nothing to run."""
    light = yaml.safe_load(DOCS_WORKFLOW.read_text())
    targets: set[str] = set()
    for job in light["jobs"].values():
        for step in job.get("steps", []):
            targets.update(re.findall(r"\bmake ([a-z-]+)", str(step.get("run", ""))))
    assert {"lint", "test-fast"} <= targets, f"the docs gate runs only {sorted(targets)}"


@pytest.mark.trace("REQ-INFRA-002")
def test_the_light_gate_does_not_pretend_to_run_the_full_one() -> None:
    """`make validate` needs `markers`, which needs the suite and a stack.

    Claiming it here would make the docs gate the half-hour it exists to avoid,
    and skipping it quietly would leave R8 unchecked for a file that carries a
    trace marker. The honest arrangement is the one in place: the graph's
    exposure to a docs edit is covered by a fast test, and that is asserted
    where somebody changing this file will read it.
    """
    parsed = yaml.safe_load(DOCS_WORKFLOW.read_text())
    targets: set[str] = set()
    for job in parsed["jobs"].values():
        for step in job.get("steps", []):
            targets.update(re.findall(r"\bmake ([a-z-]+)", str(step.get("run", ""))))
    # Read from the steps, not the file: the comment above them explains why
    # `validate` is absent, and a check on the raw text would trip on its own
    # explanation.
    assert "validate" not in targets
    assert "test" not in targets, "the full suite needs services this job has none of"
    stands_in = "test_every_trace_marker_in_docs_names_a_real_requirement"
    assert stands_in in DOCS_WORKFLOW.read_text(), (
        "the docs gate must name the fast test that stands in for `make validate`"
    )
