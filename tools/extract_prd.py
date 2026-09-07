"""One-shot generator: turn the PRD's anchor entities into requirement skeletons.

Not part of the runtime. Run once, review the output by hand, then enrich the
Acceptance sections. Refuses to overwrite an existing note, because requirement
IDs are permanent and hand-written prose must never be clobbered.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HEADING_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("US", re.compile(r"^## US-(\d{3}) — (.+)$"), "user-story"),
    ("WP", re.compile(r"^## WP-(\d{3}) (.+)$"), "work-package"),
    ("EXP", re.compile(r"^## EXP-(\d{3}) (.+)$"), "experiment"),
    ("PHASE", re.compile(r"^#{2,3} Phase (\d[A-Z]?) — (.+)$"), "phase"),
    ("NRT", re.compile(r"^### Test ([A-F]) — (.+)$"), "constraint"),
]

NUMBERED = re.compile(r"^(\d{1,2})\. (.+)$")
SECTION = re.compile(r"^#{1,3} .+$")

# Numbered-list blocks that become constraints, keyed by the heading that opens them.
NUMBERED_BLOCKS: list[tuple[str, str, str]] = [
    ("PRIN", "## 0. Інструкція для Codex", "§0"),
    ("BIAS", "# 41. Anti-Bias Rules", "§41"),
]

# Explicit acceptance-criteria cues that may appear in a heading's body, in the
# order they take priority when a section carries more than one (a Phase
# section states both Deliverables: and Acceptance: — Acceptance wins).
ACCEPTANCE_CUES: list[re.Pattern[str]] = [
    re.compile(r"^Acceptance:\s*$"),
    re.compile(r"^Done when:\s*$"),
    re.compile(r"^Metrics?:\s*$"),
    re.compile(r"^Deliverables:\s*$"),
]

NO_ACCEPTANCE_MARKER = (
    "_The PRD states no explicit acceptance criteria for this section. "
    "They must be written before this requirement leaves `draft`._"
)


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    type: str
    prd_ref: str
    prd_lines: str
    phase: str | None
    body: str
    acceptance: str


def _section_body(lines: list[str], start: int) -> tuple[str, int]:
    """Return the text under a heading, and the line index where it ends."""
    end = start + 1
    while end < len(lines) and not SECTION.match(lines[end]):
        end += 1
    return "\n".join(lines[start + 1 : end]).strip(), end


def _extract_acceptance(body: str) -> str:
    """Pull the explicit acceptance criteria out of a section's body, if any.

    Finds every cue line (Acceptance:, Done when:, Metric(s):, Deliverables:),
    picks the highest-priority one present, and returns the text between it
    and whichever cue (of any kind) comes next, or the end of the body.
    """
    lines = body.split("\n")
    cue_hits: list[tuple[int, int]] = []  # (line index, priority rank)
    for index, line in enumerate(lines):
        stripped = line.strip()
        for rank, pattern in enumerate(ACCEPTANCE_CUES):
            if pattern.match(stripped):
                cue_hits.append((index, rank))
                break

    if not cue_hits:
        return ""

    chosen_index, _ = min(cue_hits, key=lambda hit: hit[1])
    end = len(lines)
    for index, _ in cue_hits:
        if index > chosen_index:
            end = index
            break
    return "\n".join(lines[chosen_index + 1 : end]).strip()


def extract(prd_path: Path) -> list[Requirement]:
    lines = Path(prd_path).read_text().split("\n")
    found: list[Requirement] = []

    for index, line in enumerate(lines):
        for kind, pattern, type_ in HEADING_PATTERNS:
            match = pattern.match(line)
            if not match:
                continue
            token, title = match.group(1), match.group(2).strip()
            body, end = _section_body(lines, index)
            phase = token if kind == "PHASE" else None
            found.append(
                Requirement(
                    id=f"REQ-{kind}-{token}",
                    title=title,
                    type=type_,
                    prd_ref=line.lstrip("# ").strip(),
                    prd_lines=f"{index + 1}-{end}",
                    phase=phase,
                    body=body,
                    acceptance=_extract_acceptance(body),
                )
            )
            break

    for kind, heading, ref in NUMBERED_BLOCKS:
        try:
            start = lines.index(heading)
        except ValueError:
            raise ValueError(f"PRD heading not found: {heading!r}") from None
        _, end = _section_body(lines, start)
        counter = 0
        for offset in range(start + 1, end):
            match = NUMBERED.match(lines[offset].strip())
            if not match:
                continue
            counter += 1
            title = match.group(2).strip()
            found.append(
                Requirement(
                    id=f"REQ-{kind}-{counter:03d}",
                    title=title,
                    type="constraint",
                    prd_ref=ref,
                    prd_lines=f"{offset + 1}-{offset + 1}",
                    phase=None,
                    body=title,
                    # A constraint one-liner *is* its own acceptance criterion.
                    acceptance=title,
                )
            )

    return found


NOTE_TEMPLATE = """---
id: {id}
title: {title}
type: {type}
prd_ref: "{prd_ref}"
prd_lines: "{prd_lines}"
phase: {phase}
status: draft
depends_on: []
tags: []
---

## Requirement

{body}

## Acceptance

{acceptance}

## Trace

<!-- trace:begin -->
_No linked artifacts yet._
<!-- trace:end -->

## Notes

Generated from the PRD by `tools/extract_prd.py`. This section is human
territory and is never machine-rewritten.
"""


def write_notes(requirements: list[Requirement], vault_dir: Path) -> list[Path]:
    target_dir = Path(vault_dir) / "10-requirements"
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for req in requirements:
        path = target_dir / f"{req.id}.md"
        if path.exists():
            raise FileExistsError(f"{path} already exists; requirement notes are never overwritten")
        path.write_text(
            NOTE_TEMPLATE.format(
                id=req.id,
                title=req.title.replace('"', "'"),
                type=req.type,
                prd_ref=req.prd_ref.replace('"', "'"),
                prd_lines=req.prd_lines,
                phase=req.phase if req.phase is not None else "null",
                body=req.body or req.title,
                acceptance=req.acceptance or NO_ACCEPTANCE_MARKER,
            )
        )
        written.append(path)
    return written


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    reqs = extract(root / "channel_flow_prd_codex_ua_v5.md")
    paths = write_notes(reqs, root / "vault")
    print(f"wrote {len(paths)} requirement notes")
