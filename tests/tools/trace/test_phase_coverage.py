"""Check every phase's coverage claim against the real vault.

A `REQ-PHASE-*` note is a roll-up: PRD §45 lists deliverables, and the work that
delivers them lives in other requirements. Nothing in the validator's six rules
reads that relationship -- R3 checks that an edge does not name a nonexistent
requirement, and there is no edge here to check.

So each phase note carries two lists in its frontmatter. `covers:` names the
requirements that deliver it, and `not_delivered:` names the deliverables
nothing does. This module is what makes both lists mean something:

- a covering requirement that does not exist is a typo, and a typo in a coverage
  claim reads exactly like coverage;
- a covering requirement still short of `implemented` makes the phase's claim
  premature, and nothing else would notice;
- a phase at `implemented` with a non-empty `not_delivered:` list is claiming to
  be finished while listing what is missing, which is the specific dishonesty
  these two lists exist to prevent.

Every phase is `planned` today, and every one has a non-empty `not_delivered:`
list. Those two facts are the same fact, and the last test here is what keeps
them that way.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.trace.frontmatter import split_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUIREMENTS_DIR = REPO_ROOT / "vault" / "10-requirements"

#: The ladder, in order. A phase at `implemented` or later is claiming its
#: deliverables exist.
LADDER = ("draft", "specified", "planned", "tested", "implemented", "verified")
DELIVERED_FROM = LADDER.index("implemented")


def _meta(req_id: str) -> dict:
    path = REQUIREMENTS_DIR / f"{req_id}.md"
    assert path.exists(), f"{req_id} has no requirement note at {path}"
    meta, _ = split_frontmatter(path.read_text())
    return meta


def _phase_notes() -> list[Path]:
    notes = sorted(REQUIREMENTS_DIR.glob("REQ-PHASE-*.md"))
    assert notes, f"expected REQ-PHASE-* notes under {REQUIREMENTS_DIR}"
    return notes


def assert_phase_is_honest(req_id: str) -> None:
    """The three checks, applied to one phase."""
    meta = _meta(req_id)
    covers = meta.get("covers")
    gaps = meta.get("not_delivered")

    assert isinstance(covers, list), (
        f"{req_id}: a phase note must carry a `covers:` list, even an empty one. "
        "An absent list is indistinguishable from a phase nobody has mapped"
    )
    assert isinstance(gaps, list), (
        f"{req_id}: a phase note must carry a `not_delivered:` list, even an empty "
        "one. An absent list reads as 'nothing is missing'"
    )

    for covered in covers:
        covered_meta = _meta(str(covered))
        status = str(covered_meta.get("status", "draft"))
        assert status in LADDER, f"{req_id}: {covered} has an unknown status {status!r}"
        assert LADDER.index(status) >= DELIVERED_FROM, (
            f"{req_id} claims {covered} delivers part of it, but {covered} is only "
            f"{status!r}. A phase cannot be delivered by work that is not"
        )

    status = str(meta.get("status", "draft"))
    if LADDER.index(status) >= DELIVERED_FROM:
        assert not gaps, (
            f"{req_id} is {status!r} and still lists {len(gaps)} undelivered "
            f"deliverable(s): {'; '.join(str(g) for g in gaps)}. A phase is its "
            "deliverables"
        )


@pytest.mark.trace("REQ-PHASE-0")
def test_phase_0_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-0")


@pytest.mark.trace("REQ-PHASE-1")
def test_phase_1_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-1")


@pytest.mark.trace("REQ-PHASE-1A")
def test_phase_1a_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-1A")


@pytest.mark.trace("REQ-PHASE-2")
def test_phase_2_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-2")


@pytest.mark.trace("REQ-PHASE-3")
def test_phase_3_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-3")


@pytest.mark.trace("REQ-PHASE-4")
def test_phase_4_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-4")


@pytest.mark.trace("REQ-PHASE-5")
def test_phase_5_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-5")


@pytest.mark.trace("REQ-PHASE-6")
def test_phase_6_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-6")


@pytest.mark.trace("REQ-PHASE-7")
def test_phase_7_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-7")


@pytest.mark.trace("REQ-PHASE-7A")
def test_phase_7a_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-7A")


@pytest.mark.trace("REQ-PHASE-8")
def test_phase_8_coverage() -> None:
    assert_phase_is_honest("REQ-PHASE-8")


@pytest.mark.trace("REQ-INFRA-001")
def test_every_phase_note_is_checked_by_one_of_these_tests() -> None:
    """Eleven notes, eleven tests, and a marker on each.

    A phase added without a test here would carry both lists and have nobody
    read them -- and an unread claim is the thing this module exists to stop.
    """
    checked = {
        "REQ-PHASE-0",
        "REQ-PHASE-1",
        "REQ-PHASE-1A",
        "REQ-PHASE-2",
        "REQ-PHASE-3",
        "REQ-PHASE-4",
        "REQ-PHASE-5",
        "REQ-PHASE-6",
        "REQ-PHASE-7",
        "REQ-PHASE-7A",
        "REQ-PHASE-8",
    }
    on_disk = {path.stem for path in _phase_notes()}

    assert on_disk == checked


@pytest.mark.trace("REQ-INFRA-001")
def test_no_requirement_note_still_carries_the_unspecified_marker() -> None:
    """The extractor writes `ACCEPTANCE-NOT-SPECIFIED` wherever a PRD section
    states deliverables and no acceptance criteria, and a note carrying it
    cannot honestly leave `draft`.

    Ten notes carried it and none does now. The marker is not retired -- re-run
    the extractor over a section with no criteria and it comes back, meaning
    exactly what it meant before. This test is what makes its reappearance
    loud rather than quiet.
    """
    carrying = [
        path.name
        for path in sorted(REQUIREMENTS_DIR.glob("*.md"))
        if "_ACCEPTANCE-NOT-SPECIFIED" in path.read_text()
    ]

    assert carrying == [], (
        f"{', '.join(carrying)} still carry the marker; criteria have to be derived "
        "from the PRD and the derivation recorded before the note leaves draft"
    )
