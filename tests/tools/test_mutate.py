"""The mutation harness, tested (REQ-INFRA-004).

A tool that decides whether a test suite is worth having has to be worth having
itself. Each test below corresponds to a way the throwaway scripts this replaces
could report a number nobody could reproduce.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from tools import mutate
from tools.mutate import Mutation, Spec, SpecError, apply_once, sweep, verdict

SOURCE = textwrap.dedent(
    """
    def add(a: int, b: int) -> int:
        return a + b


    def scale(x: int) -> int:
        return x * 2


    def untested(n: int) -> int:
        return n + 1
    """
).lstrip()

TESTS = textwrap.dedent(
    """
    from subject import add, scale


    def test_add():
        assert add(2, 3) == 5


    def test_scale():
        assert scale(3) == 6
    """
).lstrip()


@pytest.fixture
def workspace(tmp_path: Path) -> tuple[Path, Path]:
    source = tmp_path / "subject.py"
    source.write_text(SOURCE)
    tests = tmp_path / "test_subject.py"
    tests.write_text(TESTS)
    (tmp_path / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent))\n"
    )
    return source, tests


def _spec(source: Path, tests: Path, *mutations: Mutation) -> Spec:
    return Spec(
        path=source.parent / "spec.toml", source=source, tests=tests, mutations=tuple(mutations)
    )


# --- the baseline --------------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_a_red_suite_refuses_to_be_swept(workspace: tuple[Path, Path]) -> None:
    """Against a failing suite every mutant is "caught" and the sweep reports a
    perfect score for a test file that does not run.

    None of the scripts this replaces checked it, and none was ever one broken
    import away from a meaningless clean sheet.
    """
    source, tests = workspace
    tests.write_text(TESTS + "\n\ndef test_broken():\n    assert False\n")
    spec = _spec(source, tests, Mutation(name="m", find="a + b", replace="a - b"))
    with pytest.raises(SpecError, match="does not pass unmutated"):
        sweep(spec, verbose=False)


# --- the specification has to still describe the source ------------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_a_pattern_that_no_longer_matches_is_an_error() -> None:
    """A pattern that stopped matching means the source moved underneath the
    mutation, which is exactly when a sweep must speak up rather than quietly
    measure less than it claims."""
    with pytest.raises(SpecError, match="pattern not found"):
        apply_once(SOURCE, Mutation(name="m", find="a * b", replace="a - b"))


@pytest.mark.trace("REQ-INFRA-004")
def test_an_ambiguous_pattern_is_an_error() -> None:
    """Which of several sites a mutation lands on is not something a
    specification should leave to `str.replace`."""
    with pytest.raises(SpecError, match="found 2 times"):
        apply_once("x = 1\ny = 1\n", Mutation(name="m", find="= 1", replace="= 2"))


@pytest.mark.trace("REQ-INFRA-004")
def test_a_mutation_that_does_not_parse_is_an_error() -> None:
    """Otherwise it is "caught" by the module failing to import, which is the
    most emphatic way of learning nothing -- and is how a corrupted
    specification hides.
    """
    with pytest.raises(SpecError, match="does not parse"):
        apply_once(SOURCE, Mutation(name="m", find="    return a + b\n", replace=""))


# --- the bytecode cache --------------------------------------------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_two_same_size_mutants_are_each_judged_on_their_own_code(
    workspace: tuple[Path, Path],
) -> None:
    """The flaw that produced this tool.

    Python validates `.pyc` files on `(mtime, size)`, so two consecutive
    mutations that leave the file the same length within one second reuse the
    first's bytecode -- and the second run reports the first's result. Here the
    first mutant is caught and the second is not, and both keep the file exactly
    as long, so a stale cache would report the second as caught too.
    """
    source, tests = workspace
    spec = _spec(
        source,
        tests,
        # Caught: the tests assert 2 + 3 == 5.
        Mutation(name="sum becomes difference", find="a + b", replace="a - b"),
        # Not caught by these tests -- nothing calls `untested` -- and exactly
        # the same number of characters, so both mutants leave the file the same
        # length as each other and as the original.
        Mutation(name="untested arithmetic", find="n + 1", replace="n - 1"),
    )
    results, broken = sweep(spec, verbose=False)
    assert not broken
    outcomes = {mutation.name: outcome for mutation, outcome in results}
    assert outcomes["sum becomes difference"] == mutate.CAUGHT
    assert outcomes["untested arithmetic"] == mutate.SURVIVED, (
        "the second mutant was judged on the first one's bytecode"
    )


# --- the source comes back -----------------------------------------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_the_source_is_restored_after_a_sweep(workspace: tuple[Path, Path]) -> None:
    source, tests = workspace
    spec = _spec(source, tests, Mutation(name="m", find="a + b", replace="a - b"))
    sweep(spec, verbose=False)
    assert source.read_text() == SOURCE


@pytest.mark.trace("REQ-INFRA-004")
def test_the_source_is_restored_even_when_a_mutant_hangs(
    workspace: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sweep that leaves a mutant in the tree hands the next hour to debugging
    a bug nobody wrote. That is not hypothetical: it happened on 2026-09-12 and
    cost twenty minutes against a suite that had passed in 0.16 seconds.
    """
    source, tests = workspace
    calls = {"n": 0}

    def fake_run(_: Path) -> int:
        calls["n"] += 1
        return 0 if calls["n"] == 1 else 124  # green baseline, then a hang

    monkeypatch.setattr(mutate, "_run", fake_run)
    spec = _spec(source, tests, Mutation(name="m", find="a + b", replace="a - b"))
    results, _ = sweep(spec, verbose=False)
    assert results[0][1] == mutate.HUNG
    assert source.read_text() == SOURCE


@pytest.mark.trace("REQ-INFRA-004")
def test_a_hang_counts_as_caught(workspace: tuple[Path, Path]) -> None:
    """A mutant that hangs is one a suite would never let through, and waiting
    out an infinite loop is not more information."""
    assert mutate.HUNG != mutate.SURVIVED
    results = [(Mutation(name="m", find="x", replace="y"), mutate.HUNG)]
    assert verdict(results) == []


# --- the recorded reasons are assertions with a date on them -------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_a_survivor_without_a_recorded_reason_fails() -> None:
    results = [(Mutation(name="m", find="x", replace="y"), mutate.SURVIVED)]
    assert verdict(results) == ["'m' survived and no reason is recorded"]


@pytest.mark.trace("REQ-INFRA-004")
def test_a_survivor_that_starts_being_caught_fails() -> None:
    """The reason has gone stale, and a stale reason in a vault note is worse
    than none -- it reads as understanding."""
    results = [(Mutation(name="m", find="x", replace="y", survives="unreachable"), mutate.CAUGHT)]
    problems = verdict(results)
    assert len(problems) == 1
    assert "is now caught but is recorded as surviving" in problems[0]
    assert "unreachable" in problems[0]


@pytest.mark.trace("REQ-INFRA-004")
def test_an_expected_survivor_and_an_expected_catch_both_pass() -> None:
    results = [
        (Mutation(name="a", find="x", replace="y"), mutate.CAUGHT),
        (
            Mutation(name="b", find="x", replace="y", survives="a guard nothing reaches"),
            mutate.SURVIVED,
        ),
    ]
    assert verdict(results) == []


# --- the specifications in this repository -------------------------------------


@pytest.mark.trace("REQ-INFRA-004")
def test_every_committed_specification_loads_and_still_matches_its_source() -> None:
    """The cheap half of a sweep, run on every commit: patterns that drifted, or
    that would break the module, are found in milliseconds rather than after a
    full suite run each.

    The sweep itself is slower and lives in the full gate.
    """
    specs = sorted(mutate.SPEC_DIR.glob("*.toml"))
    assert specs, "no mutation specifications are committed"
    for path in specs:
        spec = Spec.load(path)
        assert spec.source.is_file(), f"{path.name}: {spec.source} is gone"
        original = spec.source.read_text()
        for mutation in spec.mutations:
            apply_once(original, mutation)


@pytest.mark.trace("REQ-INFRA-004")
def test_every_recorded_survivor_says_why() -> None:
    """A `survives` field holding an empty string would satisfy the harness and
    tell nobody anything."""
    for path in sorted(mutate.SPEC_DIR.glob("*.toml")):
        for mutation in Spec.load(path).mutations:
            if mutation.survives is not None:
                assert len(mutation.survives) > 40, f"{path.name}: {mutation.name}"
