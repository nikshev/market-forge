"""Turn files on disk into graph nodes and edges.

One collector per artifact kind. Every collector returns (nodes, edges) and
never touches the graph, so each can be tested against a directory alone.
"""
# @trace: REQ-INFRA-001

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

from tools.trace.frontmatter import split_frontmatter
from tools.trace.model import Edge, Node

PRD_NODE_ID = "PRD"
# The trailing negative lookahead stops the greedy [0-9A-Z]+ from truncating
# a malformed id at a real, shorter existing requirement: unanchored, a typo
# like "REQ-WP-001b" would match "REQ-WP-001" and silently credit the code to
# a different requirement. With the lookahead, a trailing character that
# isn't a valid separator makes the whole token fail to match instead.
REQ_ID = r"REQ-[A-Z]+-[0-9A-Z]+(?![A-Za-z0-9])"
REQ_ID_RE = re.compile(rf"^{REQ_ID}$")
TRACE_COMMENT = re.compile(rf"@trace:\s*({REQ_ID})")

SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".pytest_cache", "dist"}
#: A gate defined in a workflow file is as much an implementation as one
#: defined in Python -- REQ-INFRA-002 is implemented by `.github/workflows`
#: and nothing else. Leaving YAML out made R8 unsatisfiable for it.
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml"}


def _notes(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.md") if not p.name.startswith("."))


def _require_id(meta: dict, path: Path) -> str:
    node_id = meta.get("id")
    if not node_id:
        raise ValueError(f"{path.name}: missing 'id' in frontmatter")
    node_id = str(node_id)
    if node_id != path.stem:
        raise ValueError(f"{path.name}: id {node_id!r} does not match filename {path.stem!r}")
    if node_id.startswith("REQ-") and not REQ_ID_RE.fullmatch(node_id):
        raise ValueError(f"{path.name}: id {node_id!r} does not match the requirement id grammar")
    return node_id


def _id_list(meta: dict, field: str) -> list[str]:
    value = meta.get(field) or []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def collect_requirements(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "10-requirements"):
        meta, _ = split_frontmatter(path.read_text())
        req_id = _require_id(meta, path)
        req_type = str(meta.get("type", ""))
        if req_type == "constraint" and "hard_gated" not in meta:
            raise ValueError(
                f"{path.name}: type: constraint requires an explicit 'hard_gated' "
                "field (true or false) -- rule R5 reads a missing field as false, "
                "so it must never be left implicit"
            )
        nodes.append(
            Node(
                id=req_id,
                kind="requirement",
                path=str(path),
                title=str(meta.get("title", "")),
                attrs={
                    "status": str(meta.get("status", "draft")),
                    "type": req_type,
                    "phase": meta.get("phase"),
                    "prd_ref": str(meta.get("prd_ref", "")),
                    "tags": _id_list(meta, "tags"),
                    "hard_gated": bool(meta.get("hard_gated", False)),
                },
            )
        )
        edges.append(Edge(src=req_id, dst=PRD_NODE_ID, kind="DERIVED_FROM"))
        for dependency in _id_list(meta, "depends_on"):
            edges.append(Edge(src=req_id, dst=dependency, kind="DEPENDS_ON"))
        # `covers:` is how a roll-up requirement -- a phase -- names the
        # requirements that deliver it. Collected as an edge rather than left in
        # frontmatter so R3 catches a misspelled id and R8 can follow it: a
        # phase's code is its covering requirements' code, and no source file
        # will ever carry a phase's own marker.
        for covered in _id_list(meta, "covers"):
            edges.append(Edge(src=req_id, dst=covered, kind="COVERS"))
    return nodes, edges


def collect_outcomes(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "40-outcomes"):
        meta, _ = split_frontmatter(path.read_text())
        out_id = _require_id(meta, path)
        nodes.append(
            Node(
                id=out_id,
                kind="outcome",
                path=str(path),
                attrs={"step": str(meta.get("step", "")), "commit": meta.get("commit")},
            )
        )
        for target in _id_list(meta, "records"):
            edges.append(Edge(src=out_id, dst=target, kind="RECORDS"))
    return nodes, edges


def collect_decisions(vault_dir: Path) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for path in _notes(vault_dir / "20-decisions"):
        meta, _ = split_frontmatter(path.read_text())
        adr_id = _require_id(meta, path)
        nodes.append(
            Node(
                id=adr_id,
                kind="decision",
                path=str(path),
                title=str(meta.get("title", "")),
                attrs={"status": str(meta.get("status", ""))},
            )
        )
        for target in _id_list(meta, "decides"):
            edges.append(Edge(src=adr_id, dst=target, kind="DECIDES"))
    return nodes, edges


def collect_specs(specs_dir: Path) -> tuple[list[Node], list[Edge]]:
    """Spec Kit writes specs/<NNN-slug>/spec.md; the node id is SPEC-<NNN-slug>."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    if not specs_dir.is_dir():
        return nodes, edges
    for spec_path in sorted(specs_dir.glob("*/spec.md")):
        meta, _ = split_frontmatter(spec_path.read_text())
        spec_id = f"SPEC-{spec_path.parent.name}"
        nodes.append(
            Node(
                id=spec_id,
                kind="spec",
                path=str(spec_path),
                attrs={"status": str(meta.get("status", "draft"))},
            )
        )
        for target in _id_list(meta, "traces"):
            edges.append(Edge(src=spec_id, dst=target, kind="SPECIFIES"))
    return nodes, edges


def _git_tracked_files(root: Path) -> set[Path] | None:
    """Absolute paths `git` tracks under `root`, or None if git/the repo is
    unavailable — callers must treat None as "cannot filter", not "nothing
    tracked".

    `-z` NUL-terminates each entry and disables the default C-quoting of
    "unusual" (including non-ASCII) filenames -- with plain `ls-files`, a
    tracked file like `café.py` prints as a quoted `"caf\\303\\251.py"`
    string, which then never matches `(root / line)`, so a real tracked
    file is silently treated as untracked and its markers vanish with no
    diagnostic.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return {(root / line).resolve() for line in result.stdout.split("\0") if line}


def collect_code(roots: Sequence[Path]) -> tuple[list[Node], list[Edge]]:
    """One node per git-tracked source file containing a `# @trace:` marker.

    An untracked scratch file must never become a node: it would change the
    committed dashboard from something nobody else can see or reproduce. If
    git is unavailable or `root` isn't a repo, fall back to unfiltered
    collection rather than raising or silently finding nothing.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    for root in roots:
        if not root.is_dir():
            continue
        tracked = _git_tracked_files(root)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in CODE_SUFFIXES:
                continue
            if SKIP_DIRS & set(path.parts):
                continue
            if tracked is not None and path.resolve() not in tracked:
                continue
            targets = TRACE_COMMENT.findall(path.read_text(errors="replace"))
            if not targets:
                continue
            file_id = str(path.relative_to(root.parent))
            nodes.append(Node(id=file_id, kind="code", path=file_id))
            for target in dict.fromkeys(targets):
                edges.append(Edge(src=file_id, dst=target, kind="IMPLEMENTS"))
    return nodes, edges


def collect_tests(dump_path: Path) -> tuple[list[Node], list[Edge]]:
    """Read the JSON written by tools.trace.pytest_plugin (see Task 6)."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    if not dump_path.is_file():
        return nodes, edges
    for entry in json.loads(dump_path.read_text()):
        node_id = entry["nodeid"]
        nodes.append(Node(id=node_id, kind="test", path=node_id.split("::", 1)[0]))
        for target in dict.fromkeys(entry["requirements"]):
            edges.append(Edge(src=node_id, dst=target, kind="VERIFIES"))
    return nodes, edges
