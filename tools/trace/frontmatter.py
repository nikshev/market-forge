"""Split YAML frontmatter from a Markdown body.

Knows nothing about requirements; it only understands the fence format.
"""
# @trace: REQ-INFRA-001

from __future__ import annotations

import yaml

FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body).

    A document without a well-formed leading fence yields ({}, original text),
    so notes that were never meant to carry metadata pass through untouched.
    Malformed YAML inside a fence raises, because that is a typo worth failing on.
    """
    stripped = text.lstrip("\n")
    if not stripped.startswith(FENCE + "\n") and stripped.rstrip() != FENCE:
        return {}, text

    lines = stripped.split("\n")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == FENCE:
            raw = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            break
    else:
        return {}, text

    if not raw.strip():
        return {}, body

    try:
        meta = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc

    if meta is None:
        return {}, body
    if not isinstance(meta, dict):
        raise ValueError(f"frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, body
