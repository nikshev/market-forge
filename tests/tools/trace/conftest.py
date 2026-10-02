"""A factory for temporary vaults, so collector and validator tests share one shape."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest


class VaultBuilder:
    def __init__(self, root: Path):
        self.root = root
        for sub in ("10-requirements", "20-decisions", "30-specs", "40-outcomes", "00-index"):
            (root / "vault" / sub).mkdir(parents=True, exist_ok=True)
        (root / "specs").mkdir(exist_ok=True)
        (root / "src").mkdir(exist_ok=True)

    @property
    def vault(self) -> Path:
        return self.root / "vault"

    @property
    def specs(self) -> Path:
        return self.root / "specs"

    def requirement(
        self,
        req_id: str,
        *,
        status: str = "draft",
        type_: str = "work-package",
        depends_on: list[str] | None = None,
        covers: list[str] | None = None,
        prd_ref: str = "§46",
        title: str = "A requirement",
        hard_gated: bool = False,
    ) -> Path:
        deps = "[]" if not depends_on else "[" + ", ".join(depends_on) + "]"
        covered = "[]" if not covers else "[" + ", ".join(covers) + "]"
        path = self.vault / "10-requirements" / f"{req_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {req_id}
                title: {title}
                type: {type_}
                hard_gated: {"true" if hard_gated else "false"}
                prd_ref: "{prd_ref}"
                phase: 0
                status: {status}
                depends_on: {deps}
                covers: {covered}
                ---

                ## Requirement

                Body.

                ## Trace

                <!-- trace:begin -->
                _Not yet generated._
                <!-- trace:end -->

                ## Notes

                Hand-written, never machine-rewritten.
                """)
        )
        return path

    def spec(self, slug: str, traces: list[str]) -> Path:
        directory = self.specs / slug
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "spec.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                traces: [{", ".join(traces)}]
                status: draft
                ---

                # Spec {slug}
                """)
        )
        return path

    def outcome(self, out_id: str, *, step: str, records: list[str]) -> Path:
        path = self.vault / "40-outcomes" / f"{out_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {out_id}
                step: {step}
                records: [{", ".join(records)}]
                commit: null
                ---

                ## What was done
                """)
        )
        return path

    def decision(self, adr_id: str, decides: list[str]) -> Path:
        path = self.vault / "20-decisions" / f"{adr_id}.md"
        path.write_text(
            textwrap.dedent(f"""\
                ---
                id: {adr_id}
                title: A decision
                status: accepted
                decides: [{", ".join(decides)}]
                date: 2026-09-07
                ---

                ## Context
                """)
        )
        return path

    def source(self, relative: str, traces: list[str]) -> Path:
        path = self.root / "src" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(f"# @trace: {t}" for t in traces)
        path.write_text(f'"""A module."""\n\n{markers}\n\n\ndef thing():\n    return 1\n')
        return path


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> VaultBuilder:
    """A temporary vault, in an environment that does not belong to the caller's git.

    Several tests here run `git init` and `git add` in `tmp_path`, and the code under
    test runs `git ls-files`. A subprocess inherits the environment, and git exports
    `GIT_INDEX_FILE` to a pre-commit hook -- an absolute path to a temporary index when
    the commit names paths. Inherited, it makes `git add` in the temporary repository
    write into the *real* repository's index while the object goes into the temporary
    one, which leaves the real index naming a blob that does not exist:
    `invalid object ... for 'src/channelflow/café.py'`, "Error building trees", and a
    rejected commit. Found on 2026-10-02 on a `git commit --only` run through the gate.

    Every `GIT_*` variable is removed rather than only that one: `GIT_DIR`,
    `GIT_WORK_TREE` and `GIT_PREFIX` redirect git in the same way.
    """
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    return VaultBuilder(tmp_path)
