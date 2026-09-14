"""What a phase note claims it has not done.

# @trace: REQ-WP-069

A phase carries four lists. `covers:` names the requirements that deliver it;
`not_delivered:`, `blocked:` and `deferred:` name what it does not, and they
mean different things:

* `not_delivered:` — work that remains and that this project can do. A phase at
  `implemented` has none, which is the rule these lists exist for.
* `blocked:` — waiting on something outside this repository. It does not hold a
  phase open, because a phase cannot deliver what it is not allowed to.
* `deferred:` — decided against, naming the decision.

They were one list until [[REQ-WP-069]]. Phase 4 held all three kinds at once,
so it could not reach `implemented` however much of it was finished, and every
answer to "what is left" counted two things nobody here could do.

**Splitting a list is trivial. What keeps it honest is that two of the three
cost something to use**, which is what these two functions charge: a blocked
entry names its blocker, and a deferred entry names a decision that exists.
Without them, moving an entry one list to the right would close any phase at
will.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

#: What a `blocked:` entry has to say. Two spellings, because the entries are
#: prose: "waits on Curve" and "waiting on an archive node" are one claim.
BLOCKER_WORDS = ("waits on", "waiting on")

_ADR = re.compile(r"\[\[(ADR-\d+)\]\]")


class DishonestPhase(AssertionError):
    """A phase note's lists say something they have not earned."""


def check_blocked(entries: Sequence[object], *, phase: str) -> None:
    """Every blocked entry names what it waits on.

    Without a blocker, "blocked" is "not started" with a better name -- and a
    better name is exactly what would let an entry be moved here to close a
    phase.
    """
    for entry in entries:
        if not any(word in str(entry).lower() for word in BLOCKER_WORDS):
            raise DishonestPhase(
                f"{phase}: {entry!r} is listed as blocked and names nothing it waits "
                "on. Without a blocker, 'blocked' is 'not started' with a better "
                "name, and moving an entry here would close the phase at will"
            )


def check_deferred(entries: Sequence[object], *, phase: str, vault: Path) -> None:
    """Every deferred entry names a decision that exists.

    Existence, not shape: `[[ADR-999]]` satisfies a pattern and defers to
    nothing, so the file is opened.
    """
    for entry in entries:
        adrs = _ADR.findall(str(entry))
        if not adrs:
            raise DishonestPhase(
                f"{phase}: {entry!r} is listed as deferred and names no decision. "
                "Deferring requires having decided"
            )
        for adr in adrs:
            if not (vault / "20-decisions" / f"{adr}.md").is_file():
                raise DishonestPhase(f"{phase}: {entry!r} defers to {adr}, which does not exist")
