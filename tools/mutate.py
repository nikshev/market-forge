"""Run a mutation sweep from a committed specification.

# @trace: REQ-INFRA-004

A mutation sweep asks whether a test suite is worth having: change the source in
a way that should break something, and see whether anything breaks. Thirty-six
outcome notes in this repository cite one, and until now they all ran from
throwaway scripts that were retyped per requirement and never committed --
so a flaw in one was a flaw in all of them, and nobody but the author could
check a claimed number.

Four things this does that those scripts did not, each for a reason that bit:

**It refuses to start on a red suite.** Against a failing suite every mutant is
"caught" and the sweep reports a perfect score for a test file that does not
run. This was never hit and was always one broken import away.

**It disables the bytecode cache.** Python validates `.pyc` files on
`(mtime, size)`, so two consecutive mutants producing files of identical size
within one second reuse the first's bytecode -- the second run then executes the
first mutant's code and reports its result. Found on 2026-09-12, in the
direction that cost work; the other direction turns a survivor into a reported
catch and shows nothing.

**A mutation that stops the module importing is an error, not a catch.** A
broken mutant turns the suite red without running it, which looks like the
strongest possible result and means nothing. It is also how a corrupted
specification hides: the first conversion of these sweeps to files lost the
leading indentation of every multi-line pattern, and those mutations "passed" as
syntax errors.

**A pattern that no longer matches is an error.** The scripts skipped it with a
note. A pattern that stopped matching means the source moved underneath the
mutation, which is exactly when a sweep must speak up rather than quietly
measure less than it claims.

**A survivor must carry a reason, and a survivor that starts being caught
fails.** Every sweep here ends with a few survivors and a paragraph explaining
why each is acceptable -- an unreachable branch, a guard a later guard covers, a
contract comment that could not be reproduced. Those paragraphs are the
accumulated understanding, and this is what keeps them from going stale.

Usage:

    .venv/bin/python -m tools.mutate tests/mutations/curve.toml
    .venv/bin/python -m tools.mutate            # every spec

Exit status is non-zero when any mutation's outcome disagrees with its
specification.
"""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import sys
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "tests" / "mutations"

#: How long a single mutated run may take. A mutant that hangs counts as caught:
#: a suite would never let it through, and waiting out an infinite loop is not
#: more information.
TIMEOUT_SECONDS = 120

#: The environment every run gets. `PYTHONDONTWRITEBYTECODE` is the whole reason
#: this is not just `subprocess.run`.
_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

CAUGHT = "caught"
SURVIVED = "survived"
HUNG = "hung"

#: pytest's exit code for a usage or collection error. A mutation that stops the
#: module importing is **not** a catch: the suite went red without running, so
#: the result says nothing about the tests. It is a broken mutation, and it hides
#: exactly the bug that produced it -- a specification whose pattern lost its
#: indentation matched at the wrong boundary and "passed" as a syntax error.
COLLECTION_ERROR = 2


class SpecError(ValueError):
    """The specification does not describe this source file any more."""


@dataclass(frozen=True)
class Mutation:
    name: str
    find: str
    replace: str
    #: Why this one is expected to survive. Absent means it must be caught.
    survives: str | None = None


@dataclass(frozen=True)
class Spec:
    path: Path
    source: Path
    tests: Path
    mutations: tuple[Mutation, ...]

    @classmethod
    def load(cls, path: Path) -> Spec:
        raw = tomllib.loads(path.read_text())
        mutations = tuple(
            Mutation(
                name=entry["name"],
                find=entry["find"],
                replace=entry["replace"],
                survives=entry.get("survives"),
            )
            for entry in raw["mutation"]
        )
        names = [mutation.name for mutation in mutations]
        if len(set(names)) != len(names):
            raise SpecError(f"{path}: duplicate mutation names")
        return cls(
            path=path,
            source=ROOT / raw["source"],
            tests=ROOT / raw["tests"],
            mutations=mutations,
        )


def _run(tests: Path) -> int:
    """The suite, in a fresh interpreter that writes no bytecode."""
    try:
        completed = subprocess.run(  # noqa: S603
            [
                sys.executable,
                "-m",
                "pytest",
                str(tests),
                "-q",
                "-x",
                "--no-header",
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=_ENV,
            cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return 124
    return completed.returncode


def apply_once(text: str, mutation: Mutation) -> str:
    """The mutated source, or an error saying why the specification is stale.

    Exactly one occurrence. Zero means the source moved; more than one means the
    mutation would silently apply to whichever came first, and which one that is
    is not something a specification should leave open.
    """
    occurrences = text.count(mutation.find)
    if occurrences == 0:
        raise SpecError(f"{mutation.name!r}: pattern not found; the source moved")
    if occurrences > 1:
        raise SpecError(f"{mutation.name!r}: pattern found {occurrences} times; ambiguous")
    mutated = text.replace(mutation.find, mutation.replace, 1)
    try:
        # Milliseconds here, against a full suite run there -- and a mutation
        # that does not parse would otherwise be "caught" by the module failing
        # to import, which is the most emphatic way of learning nothing.
        ast.parse(mutated)
    except SyntaxError as exc:
        raise SpecError(f"{mutation.name!r}: the mutated source does not parse: {exc}") from exc
    return mutated


def sweep(spec: Spec, *, verbose: bool = True) -> tuple[list[tuple[Mutation, str]], list[str]]:
    """Every mutation in one specification, against a suite proven green first."""
    original = spec.source.read_text()

    baseline = _run(spec.tests)
    if baseline != 0:
        raise SpecError(
            f"{spec.tests} does not pass unmutated (exit {baseline}). "
            "Every mutant would be reported as caught."
        )

    results: list[tuple[Mutation, str]] = []
    broken: list[str] = []
    for mutation in spec.mutations:
        try:
            mutated = apply_once(original, mutation)
        except SpecError as exc:
            broken.append(str(exc))
            print(f"  {'BROKEN':>8}  {mutation.name}", flush=True)
            continue
        try:
            spec.source.write_text(mutated)
            code = _run(spec.tests)
        finally:
            # Always. A sweep that leaves a mutant in the tree hands the next
            # hour to debugging a bug nobody wrote.
            spec.source.write_text(original)
        if code == COLLECTION_ERROR:
            broken.append(
                f"{mutation.name!r}: the mutated source does not import. A mutation must "
                "produce runnable code that behaves differently; this one broke the module, "
                "so the suite went red without running and the result means nothing."
            )
            print(f"  {'BROKEN':>8}  {mutation.name}", flush=True)
            continue
        outcome = SURVIVED if code == 0 else HUNG if code == 124 else CAUGHT
        results.append((mutation, outcome))
        if verbose:
            print(f"  {outcome:>8}  {mutation.name}", flush=True)
    return results, broken


def verdict(results: list[tuple[Mutation, str]]) -> list[str]:
    """What disagrees with the specification.

    Both directions are failures. An unexpected survivor is a gap in the tests;
    an expected survivor that is now caught means its recorded reason has gone
    stale, and a stale reason in a vault note is worse than none.
    """
    problems = []
    for mutation, outcome in results:
        if outcome == SURVIVED and mutation.survives is None:
            problems.append(f"{mutation.name!r} survived and no reason is recorded")
        if outcome != SURVIVED and mutation.survives is not None:
            problems.append(
                f"{mutation.name!r} is now {outcome} but is recorded as surviving "
                f"because: {mutation.survives}"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specs", nargs="*", type=Path, help="specification files")
    arguments = parser.parse_args()

    paths = arguments.specs or sorted(SPEC_DIR.glob("*.toml"))
    if not paths:
        print(f"no specifications under {SPEC_DIR}")
        return 1

    failures: list[str] = []
    caught = survived = 0
    started = time.monotonic()
    for path in paths:
        spec = Spec.load(path)
        print(
            f"{path.name}: {len(spec.mutations)} mutations against {spec.source.name}",
            flush=True,
        )
        results, broken = sweep(spec)
        caught += sum(1 for _, outcome in results if outcome != SURVIVED)
        survived += sum(1 for _, outcome in results if outcome == SURVIVED)
        failures += [f"{path.name}: {problem}" for problem in verdict(results) + broken]

    elapsed = time.monotonic() - started
    print(f"\n{caught} caught, {survived} survived, in {elapsed:.0f}s")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
