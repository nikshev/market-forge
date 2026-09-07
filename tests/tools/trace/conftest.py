"""A factory for temporary vaults, so collector and validator tests share one shape."""

from __future__ import annotations

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
        prd_ref: str = "§46",
        title: str = "A requirement",
        hard_gated: bool = False,
    ) -> Path:
        deps = "[]" if not depends_on else "[" + ", ".join(depends_on) + "]"
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
def vault(tmp_path: Path) -> VaultBuilder:
    return VaultBuilder(tmp_path)
