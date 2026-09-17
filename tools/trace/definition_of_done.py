"""PRD §47's nineteen conditions, and what it costs to claim one is met.

# @trace: REQ-DOD-001

§47 is the only place the PRD says what finishing means. Every one of its
conditions already had delivery behind it before [[REQ-DOD-001]] was written --
but the mapping lived nowhere. It was reconstructed by hand, by reading 103
requirement titles and grepping the source, and a mapping assembled that way is
a claim about a moment: the next requirement to change one of those areas would
not know it was answering §47, and nothing would notice when an answer stopped
being true.

**The functions here are what stop the note answering its own question.** A
roll-up that carried a mapping and checked nothing would let "done" mean "the
frontmatter says so". Each of these charges something:

* `conditions_in_prd` reads §47 out of the PRD. Not a copy and not a paraphrase
  -- the section itself, so a condition quietly reworded into something easier
  to satisfy fails against the source of truth.
* `unclaimed` refuses a condition with no covering requirement. An empty list is
  a condition nothing delivers, and §47 is then unmet rather than unmentioned.
* `undelivered` refuses a covering requirement short of `implemented`, and names
  the condition it leaves open.
* `disagreement` derives the flat `covers:` list from the per-condition ones.
  Two lists that can drift apart will.

This is the fourth time this repository has found a rule that held only because
nothing checked it -- after §34's seven, §35.3 and §35.4. §47 is the largest,
because it is the definition of done.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

#: The status ladder, in order. A covering requirement below `implemented`
#: leaves its condition open.
LADDER = ("draft", "specified", "planned", "tested", "implemented", "verified")
DELIVERED = LADDER.index("implemented")


class DishonestMapping(ValueError):
    """The §47 note claims something its own frontmatter does not support."""


def conditions_in_prd(prd: Path) -> list[str]:
    """§47's numbered conditions, read out of the PRD.

    Raises rather than returning an empty list: a parser that silently found
    nothing would make every comparison below vacuously true, which is the
    failure shape this whole requirement exists to prevent.
    """
    lines = prd.read_text().splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("# 47. ")]
    if len(starts) != 1:
        raise DishonestMapping(f"expected exactly one §47 heading, found {len(starts)}")
    start = starts[0]
    after = [i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith("# 48.")]
    if not after:
        raise DishonestMapping("§47 has no following section; the range is unbounded")
    found = [
        match.group(2).strip()
        for line in lines[start : after[0]]
        if (match := re.match(r"^(\d+)\. (.+)$", line.strip()))
    ]
    if not found:
        raise DishonestMapping("§47 states no numbered conditions; the parser found none")
    return found


def _normalise(text: str) -> str:
    """Markdown emphasis is not a rewording, and is the only licence taken."""
    return text.replace("`", "").replace("**", "").strip()


def misquoted(conditions: Sequence[Mapping[str, object]], prd: Sequence[str]) -> list[str]:
    """Conditions whose text is not §47's own, item by item."""
    if len(conditions) != len(prd):
        raise DishonestMapping(
            f"the note states {len(conditions)} conditions and §47 states {len(prd)}"
        )
    return [
        f"item {entry['item']}: note says {_normalise(str(entry['text']))!r}, "
        f"§47 says {_normalise(expected)!r}"
        for entry, expected in zip(conditions, prd, strict=True)
        if _normalise(str(entry["text"])) != _normalise(expected)
    ]


def unclaimed(conditions: Sequence[Mapping[str, object]]) -> list[str]:
    """Conditions with no covering requirement at all."""
    return [
        f"item {entry['item']}: {entry['text']}" for entry in conditions if not entry.get("covers")
    ]


def undelivered(
    conditions: Sequence[Mapping[str, object]], status_of: Mapping[str, str]
) -> list[str]:
    """Covering requirements that have not reached `implemented`, by condition."""
    short: list[str] = []
    for entry in conditions:
        for req_id in entry.get("covers") or ():
            status = status_of.get(str(req_id))
            if status is None:
                raise DishonestMapping(
                    f"item {entry['item']} names {req_id}, which has no requirement note"
                )
            if status not in LADDER:
                raise DishonestMapping(f"{req_id} has an unknown status {status!r}")
            if LADDER.index(status) < DELIVERED:
                short.append(f"item {entry['item']}: {req_id} is {status}")
    return short


def disagreement(
    conditions: Sequence[Mapping[str, object]], flat: Sequence[str]
) -> tuple[list[str], list[str]]:
    """What the flat `covers:` list holds that the conditions do not, and back."""
    union = {str(r) for entry in conditions for r in entry.get("covers") or ()}
    declared = {str(r) for r in flat}
    return sorted(declared - union), sorted(union - declared)
