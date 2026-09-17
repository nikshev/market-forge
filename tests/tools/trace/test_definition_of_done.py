"""PRD §47's nineteen conditions, checked rather than claimed (REQ-DOD-001).

§47 is the only place the PRD says what finishing means. Every one of its
conditions already had delivery behind it before this file existed -- but the
mapping was reconstructed by hand, by reading 103 requirement titles and
grepping the source. A mapping assembled that way is a claim about a moment.

The same shape has now appeared four times in this repository: §34's seven
requirements that held only because the violating code did not exist yet, §35.3
and §35.4's correctness tests that nothing enumerated, and this. §47 is the
largest, because it is the definition of done.

**These tests read the PRD.** Not a copy of it, not a paraphrase: the section is
parsed out of `channel_flow_prd_codex_ua_v5.md` and compared to the note's
`conditions:` verbatim. A condition quietly reworded into something easier to
satisfy fails against the source of truth itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.trace.definition_of_done import (
    DishonestMapping,
    conditions_in_prd,
    disagreement,
    misquoted,
    unclaimed,
    undelivered,
)
from tools.trace.frontmatter import split_frontmatter

ROOT = Path(__file__).resolve().parents[3]
PRD = ROOT / "channel_flow_prd_codex_ua_v5.md"
NOTE = ROOT / "vault" / "10-requirements" / "REQ-DOD-001.md"
REQUIREMENTS = ROOT / "vault" / "10-requirements"

#: §47's own count. Asserted so a note that lost a condition cannot report that
#: the rest are met.
CONDITIONS = 19

LADDER = ("draft", "specified", "planned", "tested", "implemented", "verified")
DELIVERED = LADDER.index("implemented")


def _note() -> dict:
    meta, _ = split_frontmatter(NOTE.read_text())
    return meta


def _prd_conditions() -> list[str]:
    return conditions_in_prd(PRD)


def _statuses() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in REQUIREMENTS.glob("*.md"):
        meta, _ = split_frontmatter(path.read_text())
        out[str(meta["id"])] = str(meta.get("status", "draft"))
    return out


def _status(req_id: str) -> str:
    path = REQUIREMENTS / f"{req_id}.md"
    assert path.exists(), f"{req_id} is named by §47's mapping and has no requirement note"
    meta, _ = split_frontmatter(path.read_text())
    return str(meta.get("status", "draft"))


@pytest.mark.trace("REQ-DOD-001")
def test_the_prd_still_states_nineteen_conditions() -> None:
    """If §47 grows a condition, this fails before anything claims to meet it."""
    found = _prd_conditions()
    assert len(found) == CONDITIONS, f"§47 now states {len(found)} conditions, not {CONDITIONS}"
    assert found[0].startswith("Non-repainting channel")
    assert found[-1].startswith("Adaptive stop management can run")


@pytest.mark.trace("REQ-DOD-001")
def test_every_condition_is_quoted_verbatim_from_the_prd() -> None:
    """A condition reworded into something easier to satisfy fails against §47."""
    wrong = misquoted(_note()["conditions"], _prd_conditions())
    assert wrong == [], "\n".join(wrong)


@pytest.mark.trace("REQ-DOD-001")
def test_the_items_are_numbered_one_to_nineteen() -> None:
    assert [int(e["item"]) for e in _note()["conditions"]] == list(range(1, CONDITIONS + 1))


@pytest.mark.trace("REQ-DOD-001")
def test_no_condition_is_unclaimed() -> None:
    """An empty list is a condition nothing delivers, and §47 is then unmet."""
    unclaimed = [(e["item"], e["text"]) for e in _note()["conditions"] if not e.get("covers")]
    assert unclaimed == [], "\n".join(f"  item {n}: {t}" for n, t in unclaimed)


@pytest.mark.trace("REQ-DOD-001")
def test_every_covering_requirement_has_been_delivered() -> None:
    """A condition whose work is still `planned` makes §47 unmet, by name."""
    short = undelivered(_note()["conditions"], _statuses())
    assert short == [], "§47 is not met:\n" + "\n".join(short)


@pytest.mark.trace("REQ-DOD-001")
def test_the_flat_covers_list_is_exactly_the_union() -> None:
    """Two lists that can disagree will, so this one is derived and checked."""
    meta = _note()
    stray, missing = disagreement(meta["conditions"], meta["covers"])
    assert (stray, missing) == ([], []), f"only in covers: {stray}; only in conditions: {missing}"


@pytest.mark.trace("REQ-DOD-001")
def test_the_mapping_reaches_more_than_a_handful_of_requirements() -> None:
    """A mapping that pointed everything at one requirement would pass the rest."""
    meta = _note()
    assert len(meta["covers"]) >= 25
    per_item = [len(e["covers"]) for e in meta["conditions"]]
    assert min(per_item) >= 1
    assert sum(per_item) >= CONDITIONS


# --- the faults, introduced on purpose --------------------------------------


def _condition(item: int, text: str, covers: list[str]) -> dict:
    return {"item": item, "text": text, "covers": covers}


@pytest.mark.trace("REQ-DOD-001")
def test_a_reworded_condition_fails_against_the_prd() -> None:
    """The point of reading §47 rather than a copy of it."""
    prd = _prd_conditions()
    softened = [
        _condition(i + 1, "Non-repainting channel mostly proven." if i == 0 else t, ["REQ-WP-006"])
        for i, t in enumerate(prd)
    ]
    wrong = misquoted(softened, prd)
    assert len(wrong) == 1
    assert "item 1" in wrong[0]


@pytest.mark.trace("REQ-DOD-001")
def test_a_condition_with_no_covering_requirement_is_named() -> None:
    found = unclaimed(
        [_condition(1, "Non-repainting channel proven.", []), _condition(2, "x", ["REQ-WP-006"])]
    )
    assert found == ["item 1: Non-repainting channel proven."]


@pytest.mark.trace("REQ-DOD-001")
@pytest.mark.parametrize("status", ["draft", "specified", "planned", "tested"])
def test_a_condition_whose_work_is_unfinished_is_named(status: str) -> None:
    """Every rung below `implemented`, including `tested`.

    `tested` is the one worth naming: it means failing tests were written, not
    that the work is done, and a bar set there would let §47 be met by a
    requirement that has no implementation at all.
    """
    short = undelivered(
        [_condition(4, "Backtest uses same signal engine.", ["REQ-WP-010", "REQ-WP-006"])],
        {"REQ-WP-010": status, "REQ-WP-006": "implemented"},
    )
    assert short == [f"item 4: REQ-WP-010 is {status}"]


@pytest.mark.trace("REQ-DOD-001")
@pytest.mark.parametrize("status", ["implemented", "verified"])
def test_a_condition_whose_work_is_finished_is_not_named(status: str) -> None:
    assert undelivered([_condition(4, "x", ["REQ-WP-010"])], {"REQ-WP-010": status}) == []


@pytest.mark.trace("REQ-DOD-001")
def test_a_covering_requirement_that_does_not_exist_is_refused() -> None:
    """A misspelled id would otherwise read as coverage."""
    with pytest.raises(DishonestMapping, match="has no requirement note"):
        undelivered([_condition(1, "x", ["REQ-WP-999"])], {"REQ-WP-006": "implemented"})


@pytest.mark.trace("REQ-DOD-001")
def test_an_unknown_status_is_refused_separately_from_a_missing_note() -> None:
    """Two different faults, two different messages -- and the first must not
    borrow the second's, or removing its check would change nothing."""
    with pytest.raises(DishonestMapping, match="unknown status"):
        undelivered([_condition(1, "x", ["REQ-WP-006"])], {"REQ-WP-006": "nearly"})


@pytest.mark.trace("REQ-DOD-001")
def test_the_two_lists_are_compared_in_both_directions() -> None:
    conditions = [_condition(1, "x", ["REQ-WP-006", "REQ-WP-010"])]
    stray, missing = disagreement(conditions, ["REQ-WP-006", "REQ-WP-099"])
    assert stray == ["REQ-WP-099"]
    assert missing == ["REQ-WP-010"]


@pytest.mark.trace("REQ-DOD-001")
def test_a_prd_that_states_no_conditions_is_refused(tmp_path: Path) -> None:
    """A parser that silently found nothing makes every comparison vacuous."""
    empty = tmp_path / "prd.md"
    empty.write_text("# 47. Definition of Done\n\nNothing numbered here.\n\n# 48. Next\n")
    with pytest.raises(DishonestMapping, match="no numbered conditions"):
        conditions_in_prd(empty)


@pytest.mark.trace("REQ-DOD-001")
def test_a_prd_with_no_section_48_is_refused(tmp_path: Path) -> None:
    """Otherwise the range runs to the end of the file and swallows §48's list."""
    unbounded = tmp_path / "prd.md"
    unbounded.write_text("# 47. Definition of Done\n\n1. Something.\n")
    with pytest.raises(DishonestMapping, match="unbounded"):
        conditions_in_prd(unbounded)


@pytest.mark.trace("REQ-DOD-001")
def test_a_note_that_lost_a_condition_is_refused() -> None:
    prd = _prd_conditions()
    with pytest.raises(DishonestMapping, match="18 conditions and §47 states 19"):
        misquoted([_condition(i + 1, t, ["REQ-WP-006"]) for i, t in enumerate(prd[:-1])], prd)
