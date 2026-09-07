"""Turn files on disk into graph nodes and edges.

One collector per artifact kind. Every collector returns (nodes, edges) and
never touches the graph, so each can be tested against a directory alone.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

from tools.trace.frontmatter import split_frontmatter
from tools.trace.model import Edge, Node

PRD_NODE_ID = "PRD"
REQ_ID = r"REQ-[A-Z]+-[0-9A-Z]+"
TRACE_COMMENT = re.compile(rf"@trace:\s*({REQ_ID})")

SKIP_DIRS = {"__pycache__", ".git", ".venv", "node_modules", ".pytest_cache"}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}


def _notes(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.md") if not p.name.startswith("."))


def _require_id(meta: dict, path: Path) -> str:
    node_id = meta.get("id")
    if not node_id:
        raise ValueError(f"{path.name}: missing 'id' in frontmatter")
    if node_id != path.stem:
        raise ValueError(f"{path.name}: id {node_id!r} does not match filename {path.stem!r}")
    return str(node_id)


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
        nodes.append(
            Node(
                id=req_id,
                kind="requirement",
                path=str(path),
                title=str(meta.get("title", "")),
                attrs={
                    "status": str(meta.get("status", "draft")),
                    "type": str(meta.get("type", "")),
                    "phase": meta.get("phase"),
                    "prd_ref": str(meta.get("prd_ref", "")),
                    "tags": _id_list(meta, "tags"),
                },
            )
        )
        edges.append(Edge(src=req_id, dst=PRD_NODE_ID, kind="DERIVED_FROM"))
        for dependency in _id_list(meta, "depends_on"):
            edges.append(Edge(src=req_id, dst=dependency, kind="DEPENDS_ON"))
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


def collect_code(roots: Sequence[Path]) -> tuple[list[Node], list[Edge]]:
    """One node per source file containing at least one `# @trace:` marker."""
    nodes: list[Node] = []
    edges: list[Edge] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in CODE_SUFFIXES:
                continue
            if SKIP_DIRS & set(path.parts):
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
