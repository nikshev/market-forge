# @trace: REQ-INFRA-006
"""The Solidity suite of SignalNotary, made visible to the trace tooling (REQ-INFRA-006).

`tools/trace/collect.py` reads `# @trace:` only from Python, TypeScript and YAML sources, and a
`VERIFIES` edge comes only from a pytest case that passed. A Solidity test can therefore not earn
one on its own. This module runs `forge test --json` once and holds **one pytest case per expected
forge
test**, so that:

- a forge test that goes red fails its own case;
- a forge test that is deleted or renamed fails its case (the name is missing from the run);
- a forge test that is not in the list fails the completeness case;
- a host without Foundry **fails** with the install command -- it does not skip, because a skip
earns no `VERIFIES` and would let a gate pass without ever having run the contract tests.

The list below is the contract between the specification and the suite: it is
`specs/142-signal-notary-contract/contracts/signal-notary-abi.md`'s table of required tests.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"

#: The behaviours the specification requires, by forge test name (no parentheses).
EXPECTED = (
    "test_commit_emits_and_records",
    "test_commit_twice_reverts_and_keeps_first",
    "test_commit_zero_hash_reverts",
    "test_resolve_emits_and_records",
    "test_resolve_uncommitted_reverts",
    "test_resolve_twice_reverts_and_keeps_first",
    "test_resolve_outcome_out_of_range_reverts",
    "test_non_owner_cannot_commit",
    "test_non_owner_cannot_resolve",
    "test_constructor_rejects_zero_owner",
    "test_owner_is_the_constructor_argument",
    "test_value_is_rejected",
    "test_block_time_is_not_bar_time",
)

INSTALL = "install Foundry: `curl -L https://foundry.paradigm.xyz | bash && foundryup`"


def _results(raw: str) -> dict[str, dict[str, object]]:
    """`{test name without (): result}` over every contract in forge's JSON report."""
    report = json.loads(raw)
    found: dict[str, dict[str, object]] = {}
    for suite in report.values():
        for name, result in suite["test_results"].items():
            found[name.removesuffix("()")] = result
    return found


@pytest.fixture(scope="module")
def forge_results() -> dict[str, dict[str, object]]:
    if shutil.which("forge") is None:
        pytest.fail(f"forge is not on PATH; the SignalNotary suite cannot run: {INSTALL}")
    proc = subprocess.run(
        ["forge", "test", "--json"],
        cwd=CONTRACTS,
        capture_output=True,
        text=True,
        timeout=300,
    )
    # forge exits non-zero when any test fails; the JSON on stdout still says which, and that is
    # more useful than the exit code, so parse first and only then complain about a missing report.
    try:
        return _results(proc.stdout)
    except (json.JSONDecodeError, KeyError) as error:
        pytest.fail(
            f"forge test produced no readable report ({error}):\n{proc.stdout}\n{proc.stderr}"
        )


@pytest.mark.trace("REQ-INFRA-006")
@pytest.mark.parametrize("name", EXPECTED)
def test_the_forge_test_exists_and_passes(
    name: str, forge_results: dict[str, dict[str, object]]
) -> None:
    assert name in forge_results, (
        f"{name} is not in the forge run (deleted or renamed?); it ran: {sorted(forge_results)}"
    )
    result = forge_results[name]
    assert result["status"] == "Success", f"{name}: {result['status']} -- {result.get('reason')}"


@pytest.mark.trace("REQ-INFRA-006")
def test_the_forge_run_holds_no_test_outside_the_list(
    forge_results: dict[str, dict[str, object]],
) -> None:
    assert EXPECTED, "the expected list is empty"
    assert len(set(EXPECTED)) == len(EXPECTED), "the expected list repeats a name"
    unlisted = sorted(set(forge_results) - set(EXPECTED))
    assert not unlisted, f"forge ran tests the specification does not list: {unlisted}"
