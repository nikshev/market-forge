"""Guard rule R5's actual coverage against the real vault, not a fixture.

R5 only reads the `hard_gated` frontmatter field, which defaults to `False`
when absent (see `tools/trace/collect.py::collect_requirements`). Nothing in
the collector or validator raises if a `REQ-BIAS-*` or `REQ-NRT-*` note is
authored without the flag -- it just silently stops being hard-gated. The
only thing standing between an omitted flag and a quietly escaped R5 is this
test: it fails the moment such a note is added, edited, or copy-pasted
without carrying `hard_gated: true`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.trace.frontmatter import split_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS_DIR = REPO_ROOT / "vault" / "10-requirements"


def _requirement_notes(prefix: str) -> list[Path]:
    notes = sorted(REQUIREMENTS_DIR.glob(f"{prefix}-*.md"))
    assert notes, f"expected at least one {prefix}-* note under {REQUIREMENTS_DIR}"
    return notes


@pytest.mark.trace("REQ-INFRA-001")
def test_every_bias_requirement_is_hard_gated():
    for path in _requirement_notes("REQ-BIAS"):
        meta, _ = split_frontmatter(path.read_text())
        assert meta.get("hard_gated") is True, (
            f"{path.name}: PRD §41 anti-bias requirements must carry "
            "`hard_gated: true` -- R5 silently stops covering a note that omits it"
        )


def test_every_nrt_requirement_is_hard_gated():
    for path in _requirement_notes("REQ-NRT"):
        meta, _ = split_frontmatter(path.read_text())
        assert meta.get("hard_gated") is True, (
            f"{path.name}: PRD §13A.28 non-repainting requirements must carry "
            "`hard_gated: true` -- R5 silently stops covering a note that omits it"
        )
