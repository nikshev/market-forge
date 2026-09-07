"""Render the traceability dashboard and refresh Trace sections in requirement notes.

Everything this module writes lives between marker comments. Text outside them
is hand-written and is never touched.
"""

from __future__ import annotations

from pathlib import Path

from tools.trace.graph import to_mermaid
from tools.trace.model import Status, TraceGraph
from tools.trace.validate import Violation

BEGIN = "<!-- trace:begin -->"
END = "<!-- trace:end -->"


def replace_between_markers(text: str, block: str) -> str:
    start = text.find(BEGIN)
    end = text.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"marker pair not found: expected {BEGIN} before {END}")
    return text[: start + len(BEGIN)] + "\n" + block.rstrip("\n") + "\n" + text[end:]


def render_requirement_trace(graph: TraceGraph, req_id: str) -> str:
    specs = sorted(e.src for e in graph.edges_into(req_id, "SPECIFIES"))
    tests = sorted(e.src for e in graph.edges_into(req_id, "VERIFIES"))
    code = sorted(e.src for e in graph.edges_into(req_id, "IMPLEMENTS"))
    outcomes = sorted(e.src for e in graph.edges_into(req_id, "RECORDS"))

    if not (specs or tests or code or outcomes):
        return "_No linked artifacts yet._"

    lines: list[str] = []
    if specs:
        lines.append("- **Specs:** " + ", ".join(f"[[{s}]]" for s in specs))
    if tests:
        lines.append("- **Tests:**")
        lines.extend(f"    - `{t}`" for t in tests)
    if code:
        lines.append("- **Code:**")
        lines.extend(f"    - `{c}`" for c in code)
    if outcomes:
        lines.append("- **Outcomes:** " + ", ".join(f"[[{o}]]" for o in outcomes))
    return "\n".join(lines)


def update_requirement_notes(graph: TraceGraph) -> tuple[list[Path], list[Path]]:
    updated: list[Path] = []
    skipped: list[Path] = []
    for node in graph.nodes_of_kind("requirement"):
        path = Path(node.path)
        text = path.read_text()
        block = render_requirement_trace(graph, node.id)
        try:
            new_text = replace_between_markers(text, block)
        except ValueError:
            skipped.append(path)
            continue
        if new_text != text:
            path.write_text(new_text)
        updated.append(path)
    return updated, skipped


def render_dashboard(graph: TraceGraph, violations: list[Violation]) -> str:
    requirements = sorted(graph.nodes_of_kind("requirement"), key=lambda n: n.id)

    lines = ["## Coverage", ""]
    lines.append("| Requirement | Type | Phase | Status | Specs | Tests | Code |")
    lines.append("|---|---|---|---|---|---|---|")
    for node in requirements:
        status = Status.parse(node.attrs.get("status")).name.lower()
        lines.append(
            "| [[{id}]] | {type} | {phase} | {status} | {specs} | {tests} | {code} |".format(
                id=node.id,
                type=node.attrs.get("type", "") or "-",
                phase=node.attrs.get("phase") if node.attrs.get("phase") is not None else "-",
                status=status,
                specs=len(graph.edges_into(node.id, "SPECIFIES")),
                tests=len(graph.edges_into(node.id, "VERIFIES")),
                code=len(graph.edges_into(node.id, "IMPLEMENTS")),
            )
        )

    lines += ["", "## Violations", ""]
    if not violations:
        lines.append("No violations.")
    else:
        lines.append("| Rule | Node | Message |")
        lines.append("|---|---|---|")
        lines.extend(f"| {v.rule} | {v.node_id} | {v.message} |" for v in violations)

    phases = sorted(
        {str(n.attrs.get("phase")) for n in requirements if n.attrs.get("phase") is not None}
    )
    lines += ["", "## Graph", ""]
    if not phases:
        lines.append(to_mermaid(graph))
    else:
        for phase in phases:
            lines.append(f"### Phase {phase}")
            lines.append("")
            lines.append(to_mermaid(graph, phase=phase))
            lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def write_dashboard(graph: TraceGraph, violations: list[Violation], path: Path) -> None:
    path = Path(path)
    text = path.read_text()
    path.write_text(replace_between_markers(text, render_dashboard(graph, violations)))
