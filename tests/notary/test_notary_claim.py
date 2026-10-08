# @trace: REQ-INFRA-007
"""What the product may say about a commit (SC-007): the measured figure, never "before"."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "notary.md"
MEASUREMENT = ROOT / "deployments" / "monad-testnet-latency.json"

#: A claim that a commit comes before a price move.
OVERCLAIM = re.compile(
    r"(before|ahead of|precede[sd]?|prior to|in advance of)\s+(a|the|any)?\s*(price\s+)?"
    r"(move|movement|pump|dump)",
    re.IGNORECASE,
)
#: ... unless the sentence is saying that it does not.
NEGATION = re.compile(r"\b(not|never|no|cannot|can't|doesn't|without|nor)\b", re.IGNORECASE)


SENTENCE_END = ".;!?"


def overclaims(text: str) -> list[str]:
    """Sentences that claim a commit precedes a move, unless the same sentence denies it.

    Prose wraps, so the unit is the paragraph with its line breaks folded away -- a negation on the
    line above ("It does not prove" / "that a signal preceded a price move") still negates. It does
    not carry across a sentence boundary: "It never lies. The commit precedes the move." is a claim.
    """
    found = []
    for paragraph in re.split(r"\n\s*\n", text):
        flat = " ".join(paragraph.split())
        for match in OVERCLAIM.finditer(flat):
            start = max(flat.rfind(mark, 0, match.start()) for mark in SENTENCE_END) + 1
            if not NEGATION.search(flat[start : match.start()]):
                found.append(flat[max(0, start) : match.end() + 40].strip())
    return found


def user_facing_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z", "README.md", "docs", "apps/web/src"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout.split(b"\0")
    suffixes = {".md", ".ts", ".tsx", ".js", ".html", ".json"}
    return [
        ROOT / name.decode()
        for name in listed
        if name and (ROOT / name.decode()).suffix in suffixes and (ROOT / name.decode()).is_file()
    ]


@pytest.mark.trace("REQ-INFRA-007")
def test_the_checker_flags_an_overclaim_and_lets_a_negation_through() -> None:
    assert overclaims("Every signal is committed before the price moves.")  # the same claim
    assert overclaims("Every signal is committed before the move.")
    assert overclaims("The commit precedes a price move, so you can trust it.")
    assert overclaims("A commit is notarized ahead of the pump.")
    assert overclaims("This does not prove a signal was committed before the move.") == []
    assert overclaims("It never claims to come before a price move.") == []


@pytest.mark.trace("REQ-INFRA-007")
def test_the_checker_follows_a_sentence_across_a_line_break_but_not_across_a_full_stop() -> None:
    wrapped = "It does not prove\nthat a signal was committed before the move; nothing claims it."
    assert overclaims(wrapped) == []
    assert overclaims("It never lies. The commit precedes the move.")
    assert overclaims("Nothing here is false.\nEvery commit is ahead of the price move.")


@pytest.mark.trace("REQ-INFRA-007")
def test_no_user_facing_text_claims_a_commit_precedes_a_price_move() -> None:
    offenders = {
        str(path.relative_to(ROOT)): overclaims(path.read_text(errors="ignore"))
        for path in user_facing_files()
    }
    assert {k: v for k, v in offenders.items() if v} == {}


@pytest.mark.trace("REQ-INFRA-007")
def test_the_documentation_quotes_the_recorded_figure_or_says_it_has_none() -> None:
    text = DOC.read_text()
    if not MEASUREMENT.exists():
        assert "not yet measured" in text.lower()
        assert not re.search(r"\bmedian\b[^.\n]*\d", text, re.IGNORECASE), (
            "docs/notary.md quotes a figure although none has been recorded"
        )
        return

    recorded = json.loads(MEASUREMENT.read_text())
    quoted = re.search(
        r"Measured: median (\d+) s, p95 (\d+) s, max (\d+) s over (\d+) records", text
    )
    assert quoted, "docs/notary.md has a recorded measurement and does not quote it"
    assert tuple(int(g) for g in quoted.groups()) == (
        recorded["median_s"],
        recorded["p95_s"],
        recorded["max_s"],
        recorded["sample"],
    )
    assert recorded["meets_criterion"] is True, "the documentation quotes an insufficient sample"
